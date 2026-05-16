"""
Multi-Layer PDF Extractor
-------------------------
Goal: produce CLEAN, LINE-PRESERVED text blocks so the downstream
question parser gets sensible input.

Extraction strategy (in order):
  1. pdfplumber  -> line-accurate text from digital PDFs
  2. PyPDF2      -> fallback if pdfplumber is missing
  3. OCR         -> scanned/image PDFs (Tesseract)

Output format (list of dicts):
    {
        "text": "Q1. What is the capital of France?",
        "page": 1,
        "line_no": 12,
        "bbox": [x0, y0, x1, y1],   # optional
        "font_size": 11.0,           # optional
        "extraction_method": "pdfplumber" | "pypdf2" | "ocr"
    }

Each dict is ONE LINE of text (not an arbitrary word cluster).
This is the key design change: the parser relies on meaningful
line boundaries to detect questions, options and answer markers.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class MultiLayerPDFExtractor:
    def __init__(self, use_ocr: bool = True, line_tolerance: float = 3.0):
        self.use_ocr = use_ocr
        self.line_tolerance = line_tolerance
        self._probe_dependencies()

    # ------------------------------------------------------------------ #
    # Dependency probing
    # ------------------------------------------------------------------ #
    def _probe_dependencies(self) -> None:
        self.has_pdfplumber = False
        self.has_pypdf2 = False
        self.has_ocr = False

        try:
            import pdfplumber  # noqa: F401
            self.has_pdfplumber = True
        except ImportError:
            logger.warning("pdfplumber not installed (pip install pdfplumber)")

        try:
            from PyPDF2 import PdfReader  # noqa: F401
            self.has_pypdf2 = True
        except ImportError:
            try:
                from pypdf import PdfReader  # noqa: F401
                self.has_pypdf2 = True
            except ImportError:
                logger.debug("PyPDF2/pypdf not installed")

        try:
            import pytesseract  # noqa: F401
            from PIL import Image  # noqa: F401
            self.has_ocr = True
        except ImportError:
            logger.debug("pytesseract/Pillow not installed - OCR disabled")

    # ------------------------------------------------------------------ #
    # Public entry point
    # ------------------------------------------------------------------ #
    def extract(self, pdf_path: str) -> List[Dict]:
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        blocks: List[Dict] = []

        if self.has_pdfplumber:
            try:
                blocks = self._extract_with_pdfplumber(pdf_path)
            except Exception as e:
                logger.error(f"pdfplumber failed: {e}")

        if not blocks and self.has_pypdf2:
            try:
                blocks = self._extract_with_pypdf2(pdf_path)
            except Exception as e:
                logger.error(f"PyPDF2 fallback failed: {e}")

        # If text yield is tiny, treat PDF as scanned and OCR it
        total_chars = sum(len(b["text"]) for b in blocks)
        if total_chars < 200 and self.use_ocr and self.has_ocr:
            logger.info("Low text yield - attempting OCR fallback")
            try:
                ocr_blocks = self._extract_with_ocr(pdf_path)
                if sum(len(b["text"]) for b in ocr_blocks) > total_chars:
                    blocks = ocr_blocks
            except Exception as e:
                logger.error(f"OCR fallback failed: {e}")

        logger.info(
            f"Extracted {len(blocks)} line-blocks from {pdf_path} "
            f"({total_chars} chars)"
        )
        return blocks

    # ------------------------------------------------------------------ #
    # pdfplumber - line-preserving extraction
    # ------------------------------------------------------------------ #
    def _extract_with_pdfplumber(self, pdf_path: str) -> List[Dict]:
        import pdfplumber

        blocks: List[Dict] = []
        line_counter = 0

        with pdfplumber.open(pdf_path) as pdf:
            for page_idx, page in enumerate(pdf.pages):
                page_num = page_idx + 1

                # Use word-level data so we can group into LINES by y-position.
                try:
                    words = page.extract_words(
                        extra_attrs=["fontname", "size"],
                        keep_blank_chars=False,
                        use_text_flow=True,
                    )
                except Exception:
                    words = page.extract_words()

                if not words:
                    # Last-resort: page.extract_text already returns newline-split text
                    raw = page.extract_text() or ""
                    for raw_line in raw.splitlines():
                        text = raw_line.strip()
                        if text:
                            line_counter += 1
                            blocks.append({
                                "text": text,
                                "page": page_num,
                                "line_no": line_counter,
                                "extraction_method": "pdfplumber",
                            })
                    continue

                # Group words into lines by top-coordinate within tolerance.
                words_sorted = sorted(words, key=lambda w: (round(w["top"], 1), w["x0"]))
                current_line: List[Dict] = []
                current_top: Optional[float] = None

                def flush(line_words: List[Dict]) -> None:
                    nonlocal line_counter
                    if not line_words:
                        return
                    line_words_sorted = sorted(line_words, key=lambda w: w["x0"])
                    text = " ".join(w["text"] for w in line_words_sorted).strip()
                    if not text:
                        return
                    line_counter += 1
                    x0 = min(w["x0"] for w in line_words_sorted)
                    y0 = min(w["top"] for w in line_words_sorted)
                    x1 = max(w["x1"] for w in line_words_sorted)
                    y1 = max(w["bottom"] for w in line_words_sorted)
                    avg_size = sum(
                        float(w.get("size", 10)) for w in line_words_sorted
                    ) / len(line_words_sorted)
                    blocks.append({
                        "text": text,
                        "page": page_num,
                        "line_no": line_counter,
                        "bbox": [x0, y0, x1, y1],
                        "font_size": round(avg_size, 1),
                        "extraction_method": "pdfplumber",
                    })

                for w in words_sorted:
                    top = w["top"]
                    if current_top is None:
                        current_top = top
                        current_line = [w]
                        continue
                    if abs(top - current_top) <= self.line_tolerance:
                        current_line.append(w)
                    else:
                        flush(current_line)
                        current_line = [w]
                        current_top = top
                flush(current_line)

        return blocks

    # ------------------------------------------------------------------ #
    # PyPDF2 fallback - only when pdfplumber unavailable
    # ------------------------------------------------------------------ #
    def _extract_with_pypdf2(self, pdf_path: str) -> List[Dict]:
        try:
            from PyPDF2 import PdfReader
        except ImportError:
            from pypdf import PdfReader

        reader = PdfReader(pdf_path)
        blocks: List[Dict] = []
        line_counter = 0

        for page_idx, page in enumerate(reader.pages):
            page_num = page_idx + 1
            try:
                raw = page.extract_text() or ""
            except Exception as e:
                logger.warning(f"Page {page_num} extraction failed: {e}")
                continue
            for raw_line in raw.splitlines():
                text = raw_line.strip()
                if text:
                    line_counter += 1
                    blocks.append({
                        "text": text,
                        "page": page_num,
                        "line_no": line_counter,
                        "extraction_method": "pypdf2",
                    })

        return blocks

    # ------------------------------------------------------------------ #
    # OCR fallback - for scanned PDFs
    # ------------------------------------------------------------------ #
    def _extract_with_ocr(self, pdf_path: str) -> List[Dict]:
        from pdf2image import convert_from_path
        import pytesseract

        images = convert_from_path(pdf_path)
        blocks: List[Dict] = []
        line_counter = 0

        for i, image in enumerate(images):
            page_num = i + 1
            data = pytesseract.image_to_data(
                image, output_type=pytesseract.Output.DICT
            )
            n = len(data["text"])
            current_line_words: List[Dict] = []
            last_line_num = -1

            def flush_ocr(words: List[Dict]) -> None:
                nonlocal line_counter
                if not words:
                    return
                text = " ".join(w["text"] for w in words).strip()
                if not text:
                    return
                line_counter += 1
                x0 = min(w["left"] for w in words)
                y0 = min(w["top"] for w in words)
                x1 = max(w["left"] + w["width"] for w in words)
                y1 = max(w["top"] + w["height"] for w in words)
                blocks.append({
                    "text": text,
                    "page": page_num,
                    "line_no": line_counter,
                    "bbox": [x0, y0, x1, y1],
                    "extraction_method": "ocr",
                })

            for j in range(n):
                try:
                    conf = int(data["conf"][j])
                except (ValueError, TypeError):
                    conf = -1
                token = data["text"][j].strip()
                if conf < 30 or not token:
                    continue
                line_num = (data["block_num"][j], data["par_num"][j], data["line_num"][j])
                if last_line_num != -1 and line_num != last_line_num:
                    flush_ocr(current_line_words)
                    current_line_words = []
                last_line_num = line_num
                current_line_words.append({
                    "text": token,
                    "left": data["left"][j],
                    "top": data["top"][j],
                    "width": data["width"][j],
                    "height": data["height"][j],
                })
            flush_ocr(current_line_words)

        return blocks
