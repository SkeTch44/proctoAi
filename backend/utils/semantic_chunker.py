
import re
from typing import List, Dict, Any

class SemanticChunker:
    """
    Chunk PDF blocks using:
    - Page boundaries
    - Font size changes
    - Keywords (Q., Answer, Explanation)
    """
    
    def __init__(self):
        self.question_starters = [
            re.compile(r'^Q\s*[\.:]', re.I),
            re.compile(r'^Question\s*\d+', re.I),
            re.compile(r'^\d+[\.:]\s'),              # 1. or 1:
            re.compile(r'^\(\d+\)\s')                 # (1)
        ]
        
        self.answer_starters = [
            re.compile(r'^Ans\s*:', re.I),
            re.compile(r'^Answer\s*:', re.I),
            re.compile(r'^Sol\s*:', re.I),
            re.compile(r'^Solution\s*:', re.I),
            re.compile(r'^Explanation\s*:', re.I),
            re.compile(r'^Correct Option\s*:', re.I)
        ]
        
        self.option_indicators = [
            re.compile(r'^\([A-Da-d]\)\s'),           # (a)
            re.compile(r'^[A-Da-d][\.:]\s'),          # A. or A:
        ]

    def chunk(self, blocks: List[Dict]) -> List[Dict]:
        """
        Group blocks into semantic chunks (potential questions).
        
        Strategy:
        1. Iterate through blocks.
        2. If a block looks like a "Start of Question" (via regex or font size), start new chunk.
        3. Else, append to current chunk.
        4. Calculate confidence for each chunk.
        """
        chunks = []
        current_chunk_text = []
        current_chunk_blocks = []
        current_page = -1
        
        # Calculate average font size to detect headers
        all_font_sizes = [b.get('font_size', 10) for b in blocks]
        avg_font_size = sum(all_font_sizes) / len(all_font_sizes) if all_font_sizes else 10.0
        
        # Helper to finalize current chunk
        def finalize_chunk():
            if current_chunk_text:
                full_text = "\n".join(current_chunk_text)
                confidence = self._calculate_confidence(full_text, current_chunk_blocks, avg_font_size)
                
                # Assign a type hint
                type_hint = "unknown"
                if confidence > 0.6:
                    type_hint = "possible_question"
                
                chunks.append({
                    "chunk_id": f"c_{len(chunks)+1}_{current_chunk_blocks[0]['block_id']}",
                    "text": full_text,
                    "page": current_chunk_blocks[0]['page'],
                    "bbox": current_chunk_blocks[0]['bbox'], # approx valid
                    "type_hint": type_hint,
                    "confidence": confidence,
                    "blocks_count": len(current_chunk_blocks)
                })
        
        for block in blocks:
            text = block.get('text', '').strip()
            page = block.get('page', 1)
            font_size = block.get('font_size', 10)
            
            is_new_question = False
            
            # Criterion 1: Page boundary (Strict split, usually good for safety)
            # Actually, questions can span pages. Let's NOT split strictly on page unless it's a hard break.
            # But for simplicity in Phase 0, let's keep chunks page-localized or handle spanning later.
            # Let's simple-case: split on page for now to avoid massive context.
            if page != current_page and current_page != -1:
                finalize_chunk()
                current_chunk_text = []
                current_chunk_blocks = []
                # Fallthrough to start new chunk
            
            current_page = page

            # Criterion 2: Explicit Question Numbering (e.g., "1. What is...")
            for pattern in self.question_starters:
                if pattern.match(text):
                    is_new_question = True
                    break
            
            # Criterion 3: Explicit Header Styling (Font significantly larger)
            # Only if it also looks somewhat like a question or topic
            if font_size > avg_font_size * 1.2:
                # Big text is often a new section -> likely new chunk
                is_new_question = True
            
            if is_new_question and current_chunk_text:
                finalize_chunk()
                current_chunk_text = []
                current_chunk_blocks = []
            
            current_chunk_text.append(text)
            current_chunk_blocks.append(block)
            
        # Final flush
        finalize_chunk()
        
        return chunks

    def _calculate_confidence(self, text: str, blocks: List[Dict], avg_font_size: float) -> float:
        """Heuristic scoring for likelihood of being a valid Q&A item"""
        score = 0.0
        
        # 1. Structure: Ends with question mark?
        if '?' in text:
            score += 0.3
            
        # 2. Keywords: Starts with "Q." or similar
        for p in self.question_starters:
            if p.match(text):
                score += 0.4
                break
                
        # 3. Content: Has "Answer:" inside?
        # A chunk might contain Q and A together
        for p in self.answer_starters:
            if p.search(text):
                score += 0.3
                break
                
        # 4. Content: Has Multiple Choice Options?
        # Looking for (A), (B) etc.
        option_count = 0
        for p in self.option_indicators:
            # Count occurrences roughly
            option_count += len(p.findall(text))
        
        if option_count >= 2:
            score += 0.4
            
        return min(round(score, 2), 1.0)
