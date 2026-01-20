import logging
from typing import List, Optional
import re

logger = logging.getLogger(__name__)

class PDFParser:
    """
    PDF Parser with intelligent chunking strategy
    
    Features:
    - Text extraction from PDF
    - Overlapping sliding window chunking
    - Metadata extraction
    """
    
    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        """
        Initialize PDF Parser
        
        Args:
            chunk_size: Target size of each chunk in tokens (approximate)
            overlap: Number of tokens to overlap between chunks
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        
    def extract_text(self, file_path: str) -> Optional[str]:
        """
        Extract raw text from PDF
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Extracted text or None if failed
        """
        try:
            from PyPDF2 import PdfReader
            
            reader = PdfReader(file_path)
            text_parts = []
            
            for page_num, page in enumerate(reader.pages):
                try:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
                except Exception as e:
                    logger.warning(f"Failed to extract text from page {page_num}: {e}")
            
            full_text = "\n".join(text_parts)
            logger.info(f"Extracted {len(full_text)} characters from {len(reader.pages)} pages")
            return full_text
            
        except ImportError:
            logger.error("PyPDF2 not installed. Install with: pip install PyPDF2")
            return None
        except Exception as e:
            logger.error(f"Failed to extract text from PDF {file_path}: {e}")
            return None
    
    def extract_text_with_chunking(self, file_path: str) -> List[str]:
        """
        Extract text from PDF and split into overlapping chunks
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            List of text chunks
        """
        text = self.extract_text(file_path)
        if not text:
            return []
        
        return self.chunk_text(text)
    
    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks using sliding window
        
        Args:
            text: Input text
            
        Returns:
            List of text chunks
        """
        # Clean and normalize text
        text = self._clean_text(text)
        
        # Split into sentences for better chunking boundaries
        sentences = self._split_into_sentences(text)
        
        if not sentences:
            return []
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence.split())
            
            # If adding this sentence exceeds chunk size, save current chunk
            if current_length + sentence_length > self.chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                
                # Create overlap by keeping last few sentences
                overlap_sentences = []
                overlap_length = 0
                for s in reversed(current_chunk):
                    s_len = len(s.split())
                    if overlap_length + s_len <= self.overlap:
                        overlap_sentences.insert(0, s)
                        overlap_length += s_len
                    else:
                        break
                
                current_chunk = overlap_sentences
                current_length = overlap_length
            
            current_chunk.append(sentence)
            current_length += sentence_length
        
        # Add final chunk
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        logger.info(f"Created {len(chunks)} chunks from text")
        return chunks
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters that might interfere
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        return text.strip()
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Simple sentence splitting (can be improved with NLTK)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def extract_metadata(self, file_path: str) -> dict:
        """
        Extract metadata from PDF
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Dictionary of metadata
        """
        try:
            from PyPDF2 import PdfReader
            
            reader = PdfReader(file_path)
            metadata = {
                'num_pages': len(reader.pages),
                'file_path': file_path
            }
            
            # Extract PDF metadata if available
            if reader.metadata:
                metadata.update({
                    'title': reader.metadata.get('/Title', ''),
                    'author': reader.metadata.get('/Author', ''),
                    'subject': reader.metadata.get('/Subject', ''),
                    'creator': reader.metadata.get('/Creator', '')
                })
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to extract metadata from PDF: {e}")
            return {'file_path': file_path}

def parse_pdf(file_storage) -> str:
    """
    Wrapper function to parse PDF from Flask FileStorage object
    """
    try:
        from PyPDF2 import PdfReader
        
        # Determine if it's a path or file object
        if isinstance(file_storage, str):
            reader = PdfReader(file_storage)
        else:
            # Assume it's a file-like object (FileStorage)
            reader = PdfReader(file_storage)
            
        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
                
        return "\n".join(text_parts)
        
    except Exception as e:
        logger.error(f"Error in parse_pdf wrapper: {e}")
        return ""
