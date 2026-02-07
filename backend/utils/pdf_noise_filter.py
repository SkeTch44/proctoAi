
import re
from typing import Dict, List

class PDFNoiseFilter:
    """Rule-based noise removal (NO LLM)"""
    
    NOISE_PATTERNS = [
        r'Page \d+ of \d+',       # Page numbers
        r'Page \d+',              # Simple page numbers
        r'©\s*\d{4}',             # Copyright
        r'Copyright',             # Copyright text
        r'All rights reserved',   # Legal text
        r'www\.\S+',              # URLs
        r'http[s]?://\S+',        # HTTP links
        r'^\d+$',                 # Standalone numbers (often page numbers)
        r'^\s*$'                  # Empty strings
    ]
    
    def __init__(self):
        self.compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.NOISE_PATTERNS]

    def filter_blocks(self, blocks: List[Dict]) -> List[Dict]:
        """Filter a list of blocks, returning only valid valid ones"""
        return [b for b in blocks if self.is_valid_block(b)]

    def is_valid_block(self, block: Dict) -> bool:
        """Returns True if block should be kept"""
        text = block.get('text', '').strip()
        
        # Remove short blocks (likely headers/footers or artifacts)
        # Exception: "Q1." or "Ans:" might be short but valid, handled by regex
        if len(text) < 3:
            return False
            
        # Check against noise patterns
        for pattern in self.compiled_patterns:
            if pattern.search(text):
                return False
                
        # Check for header/footer via bbox (heuristic)
        # Assuming A4 page (approx 842 height points)
        # Top 5% and Bottom 5% usually contain noise
        # This requires page dimensions which we might not have perfectly
        # For now, rely on text patterns as they are safer
        
        return True
