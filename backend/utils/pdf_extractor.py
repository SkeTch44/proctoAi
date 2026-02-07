
import logging
import os
import re
from typing import List, Dict, Optional, Tuple, Union
import math

logger = logging.getLogger(__name__)

class MultiLayerPDFExtractor:
    """
    3-layer PDF extraction pipeline:
    1. Text PDF -> pdfplumber (Fast, accurate for digital PDFs)
    2. Scanned PDF -> pytesseract (OCR fallback)
    3. Layout -> pdfminer.six (Structure analysis)
    """
    
    def __init__(self, use_ocr: bool = True):
        self.use_ocr = use_ocr
        self._check_dependencies()
        
    def _check_dependencies(self):
        """Check availability of extraction libraries"""
        self.has_pdfplumber = False
        self.has_ocr = False
        self.has_pdfminer = False
        
        try:
            import pdfplumber
            self.has_pdfplumber = True
        except ImportError:
            logger.warning("pdfplumber not found. Install with: pip install pdfplumber")
            
        try:
            import pytesseract
            from PIL import Image
            self.has_ocr = True
        except ImportError:
            logger.warning("pytesseract/Pillow not found. OCR disabled.")
            
        try:
            from pdfminer.high_level import extract_pages
            self.has_pdfminer = True
        except ImportError:
            logger.warning("pdfminer.six not found. Layout analysis disabled.")

    def extract(self, pdf_path: str) -> List[Dict]:
        """
        Extract content from PDF with best available method
        
        Returns:
        [
            {
                "text": "...",
                "page": 4,
                "bbox": [x1, y1, x2, y2],
                "font_size": 11,
                "block_id": "p4_b12",
                "extraction_method": "text" | "ocr" | "layout"
            }
        ]
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            
        # Try pure text extraction first (fastest & most accurate for digital PDFs)
        blocks = []
        if self.has_pdfplumber:
            try:
                blocks = self._extract_with_pdfplumber(pdf_path)
            except Exception as e:
                logger.error(f"pdfplumber extraction failed: {e}")
        
        # If extraction yielded little text, try OCR if enabled
        char_count = sum(len(b['text']) for b in blocks)
        if char_count < 100 and self.use_ocr and self.has_ocr:
            logger.info("Low text yield. Attempting OCR fallback...")
            try:
                ocr_blocks = self._extract_with_ocr(pdf_path)
                if sum(len(b['text']) for b in ocr_blocks) > char_count:
                    blocks = ocr_blocks
                    logger.info("OCR extraction successful")
            except Exception as e:
                logger.error(f"OCR extraction failed: {e}")
                
        # If we have blocks but missing layout info, try to enrich with pdfminer
        # (pdfplumber usually provides good layout data, so this is secondary)
        
        return blocks

    def _extract_with_pdfplumber(self, pdf_path: str) -> List[Dict]:
        import pdfplumber
        
        parameters = {
            "vertical_strategy": "lines", 
            "horizontal_strategy": "lines",
            "intersection_y_tolerance": 5
        }
        
        blocks = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                # Extract words to get detailed font info and generic layout
                # We group words into visual blocks based on proximity
                
                # Simple extraction: extract_words gives x0,top,x1,bottom,text,fontname,size
                words = page.extract_words(extra_attrs=['fontname', 'size'])
                
                # Group words into lines/blocks (basic clustering)
                current_block = []
                current_y = -1
                
                for word in words:
                    # New line detection (tolerance of 5 units)
                    if current_y == -1:
                        current_y = word['top']
                    
                    if abs(word['top'] - current_y) > 5:
                        # Flush current block
                        if current_block:
                            blocks.append(self._create_block_from_words(current_block, page_num + 1))
                        current_block = []
                        current_y = word['top']
                    
                    current_block.append(word)
                
                # Flush final block
                if current_block:
                    blocks.append(self._create_block_from_words(current_block, page_num + 1))
                    
        return blocks

    def _create_block_from_words(self, words: List[Dict], page_num: int) -> Dict:
        """Aggregate words into a block"""
        text = " ".join(w['text'] for w in words)
        
        # Calculate bounding box
        x0 = min(w['x0'] for w in words)
        top = min(w['top'] for w in words)
        x1 = max(w['x1'] for w in words)
        bottom = max(w['bottom'] for w in words)
        
        # Average font size (weighted by text length might be better, but average is ok)
        avg_font_size = sum(float(w.get('size', 10)) for w in words) / len(words)
        
        return {
            "text": text,
            "page": page_num,
            "bbox": [x0, top, x1, bottom],
            "font_size": round(avg_font_size, 1),
            "block_id": f"p{page_num}_b{int(top)}_{int(x0)}", # Deterministic ID based on position
            "extraction_method": "pdfplumber"
        }

    def _extract_with_ocr(self, pdf_path: str) -> List[Dict]:
        """Convert PDF to images and run Tesseract"""
        from pdf2image import convert_from_path
        import pytesseract
        
        # Convert PDF to list of images
        images = convert_from_path(pdf_path)
        blocks = []
        
        for i, image in enumerate(images):
            # Get verbose data including boxes, confidences, line and page numbers
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            
            n_boxes = len(data['text'])
            current_line_words = []
            last_line_num = -1
            
            for j in range(n_boxes):
                if int(data['conf'][j]) > 30 and data['text'][j].strip():
                    line_num = data['line_num'][j]
                    
                    if line_num != last_line_num:
                        if current_line_words:
                            blocks.append(self._create_ocr_block(current_line_words, i + 1))
                        current_line_words = []
                        last_line_num = line_num
                    
                    current_line_words.append({
                        'text': data['text'][j],
                        'left': data['left'][j],
                        'top': data['top'][j],
                        'width': data['width'][j],
                        'height': data['height'][j]
                    })
            
            if current_line_words:
                 blocks.append(self._create_ocr_block(current_line_words, i + 1))
                 
        return blocks

    def _create_ocr_block(self, words: List[Dict], page_num: int) -> Dict:
        text = " ".join(w['text'] for w in words)
        
        x0 = min(w['left'] for w in words)
        y0 = min(w['top'] for w in words)
        x1 = max(w['left'] + w['width'] for w in words)
        y1 = max(w['top'] + w['height'] for w in words)
        
        # Estimate font size from height
        avg_height = sum(w['height'] for w in words) / len(words)
        
        return {
            "text": text,
            "page": page_num,
            "bbox": [x0, y0, x1, y1],
            "font_size": round(avg_height * 0.75, 1), # Approx conversion px -> pt
            "block_id": f"p{page_num}_b{int(y0)}_{int(x0)}_ocr",
            "extraction_method": "ocr"
        }
