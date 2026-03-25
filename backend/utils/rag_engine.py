import os
import json
import logging
import pickle
from typing import List, Dict, Optional, Tuple
# import numpy as np # Lazy load if possible, or keep if lightweight
# from sentence_transformers import SentenceTransformer # Moved to lazy property

logger = logging.getLogger(__name__)

class RAGEngine:
    """
    Retrieval-Augmented Generation Engine using FAISS and Sentence Transformers
    
    Features:
    - Document chunking and embedding
    - Semantic search using FAISS
    - Persistent storage
    - Metadata tracking
    """
    
    def __init__(self, store_path: str = "backend/db/rag_store", model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize RAG Engine (Lazy Loading)
        
        Args:
            store_path: Path to store FAISS index and metadata
            model_name: Sentence transformer model name
        """
        self.store_path = store_path
        self.model_name = model_name
        self.index_path = os.path.join(store_path, "faiss_index.bin")
        self.metadata_path = os.path.join(store_path, "metadata.pkl")
        
        # Lazy initialization variables
        self._model = None
        self._index = None
        self._metadata = None
        self._embedding_dim = None

    @property
    def model(self):
        """Lazy load SentenceTransformer model"""
        if self._model is None:
            logger.info(f"Lazy loading sentence transformer model: {self.model_name}")
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
        return self._model

    @property
    def embedding_dim(self):
        """Lazy load embedding dimension"""
        if self._embedding_dim is None:
            self._embedding_dim = self.model.get_sentence_embedding_dimension()
        return self._embedding_dim

    @property
    def index(self):
        """Lazy load FAISS index"""
        if self._index is None:
            self._load_or_create_index()
        return self._index

    @property
    def metadata(self):
        """Lazy load metadata"""
        if self._metadata is None:
            if self._index is None: # Metadata is loaded with index
                self._load_or_create_index()
        return self._metadata

    @metadata.setter
    def metadata(self, value):
        self._metadata = value

    def _load_or_create_index(self):
        """Load existing FAISS index or create new one"""
        # Ensure store directory exists when we actually need it
        os.makedirs(self.store_path, exist_ok=True)

        try:
            import faiss
        except ImportError:
            logger.error("FAISS not installed. Install with: pip install faiss-cpu")
            raise ImportError("faiss-cpu is required for RAG engine")
        
        if os.path.exists(self.index_path) and os.path.exists(self.metadata_path):
            try:
                # Load existing index
                self._index = faiss.read_index(self.index_path)
                with open(self.metadata_path, 'rb') as f:
                    self._metadata = pickle.load(f)
                logger.info(f"Loaded existing FAISS index with {self._index.ntotal} vectors")
            except Exception as e:
                logger.warning(f"Failed to load existing index: {e}. Creating new index.")
                self._create_new_index()
        else:
            self._create_new_index()
    
    def _create_new_index(self):
        """Create a new FAISS index"""
        import faiss
        # Using IndexFlatL2 for exact search (can be upgraded to IndexIVFFlat for larger datasets)
        self._index = faiss.IndexFlatL2(self.embedding_dim)
        self._metadata = []
        logger.info(f"Created new FAISS index with dimension {self.embedding_dim}")
    
    def _save_index(self):
        """Persist FAISS index and metadata to disk"""
        try:
            import faiss
            faiss.write_index(self.index, self.index_path)
            with open(self.metadata_path, 'wb') as f:
                pickle.dump(self.metadata, f)
            logger.info(f"Saved FAISS index with {self.index.ntotal} vectors")
        except Exception as e:
            logger.error(f"Failed to save FAISS index: {e}")
    
    def add_document(self, doc_id: str, chunks: List[str], metadata: Optional[Dict] = None) -> int:
        """
        Add document chunks to the RAG store
        
        Args:
            doc_id: Unique document identifier
            chunks: List of text chunks
            metadata: Optional metadata for the document
            
        Returns:
            Number of chunks added
        """
        if not chunks:
            logger.warning(f"No chunks provided for document {doc_id}")
            return 0
        
        try:
            # Generate embeddings for all chunks
            logger.info(f"Generating embeddings for {len(chunks)} chunks from document {doc_id}")
            embeddings = self.model.encode(chunks, show_progress_bar=False, convert_to_numpy=True)
            
            # Add to FAISS index
            self.index.add(embeddings.astype('float32'))
            
            # Store metadata for each chunk
            base_metadata = metadata or {}
            for i, chunk in enumerate(chunks):
                chunk_metadata = {
                    'doc_id': doc_id,
                    'chunk_id': f"{doc_id}_chunk_{i}",
                    'chunk_index': i,
                    'text': chunk,
                    **base_metadata
                }
                self.metadata.append(chunk_metadata)
            
            # Persist to disk
            self._save_index()
            
            logger.info(f"Added {len(chunks)} chunks from document {doc_id} to RAG store")
            return len(chunks)
            
        except Exception as e:
            logger.error(f"Failed to add document {doc_id}: {e}")
            return 0
    
    def search(self, query: str, k: int = 3, min_score: float = 0.0) -> List[Dict]:
        """
        Search for relevant chunks using semantic similarity
        
        Args:
            query: Search query
            k: Number of results to return
            min_score: Minimum similarity score (lower is better for L2 distance)
            
        Returns:
            List of dicts with 'text', 'score', and metadata
        """
        if self.index.ntotal == 0:
            logger.warning("RAG store is empty. No results to return.")
            return []
        
        try:
            # Generate query embedding
            query_embedding = self.model.encode([query], convert_to_numpy=True).astype('float32')
            
            # Search FAISS index
            k = min(k, self.index.ntotal)  # Don't request more than available
            distances, indices = self.index.search(query_embedding, k)
            
            # Build results
            results = []
            for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
                if idx < len(self.metadata):
                    result = {
                        'rank': i + 1,
                        'score': float(distance),
                        'text': self.metadata[idx]['text'],
                        'chunk_id': self.metadata[idx]['chunk_id'],
                        'doc_id': self.metadata[idx]['doc_id'],
                        'metadata': {k: v for k, v in self.metadata[idx].items() 
                                   if k not in ['text', 'chunk_id', 'doc_id']}
                    }
                    results.append(result)
            
            logger.info(f"Retrieved {len(results)} chunks for query: '{query[:50]}...'")
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def get_stats(self) -> Dict:
        """Get statistics about the RAG store"""
        unique_docs = len(set(m['doc_id'] for m in self.metadata))
        return {
            'total_chunks': self.index.ntotal,
            'total_documents': unique_docs,
            'embedding_dimension': self.embedding_dim,
            'model_name': self.model_name
        }
    
    def clear(self):
        """Clear all data from the RAG store"""
        self._create_new_index()
        self._save_index()
        logger.info("RAG store cleared")
