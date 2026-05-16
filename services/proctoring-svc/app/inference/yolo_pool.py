"""
YOLO model pool — single model instance shared across requests.

Key optimizations (P4 items implemented here):
  - Single model load (no per-request instantiation)
  - Batch inference: accumulate frames, run forward pass on N at once
  - Perceptual hash skip: if frame is too similar to last, skip inference
"""

import logging
import threading
from typing import List, Optional, Tuple

import numpy as np

logger = logging.getLogger("proctoring-svc.yolo")

_model = None
_lock = threading.Lock()


def _load_model(model_path: str):
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                try:
                    from ultralytics import YOLO
                    _model = YOLO(model_path)
                    logger.info(f"YOLO model loaded from {model_path}")
                except Exception as e:
                    logger.error(f"Failed to load YOLO model: {e}")
                    raise
    return _model


def detect_persons(
    frames: List[np.ndarray],
    model_path: str = "yolov8n.pt",
    confidence: float = 0.5,
) -> List[dict]:
    """
    Run person detection on a batch of frames.

    Returns list of dicts:
        {"frame_idx": 0, "persons": 2, "boxes": [...], "confidences": [...]}
    """
    model = _load_model(model_path)
    results = model(frames, conf=confidence, classes=[0], verbose=False)  # class 0 = person

    detections = []
    for idx, result in enumerate(results):
        boxes = result.boxes
        detections.append({
            "frame_idx": idx,
            "persons": len(boxes),
            "boxes": boxes.xyxy.tolist() if len(boxes) > 0 else [],
            "confidences": boxes.conf.tolist() if len(boxes) > 0 else [],
        })

    return detections


def compute_phash(frame: np.ndarray, hash_size: int = 8) -> Optional[int]:
    """Compute a perceptual hash for frame-skip decisions."""
    try:
        from PIL import Image
        img = Image.fromarray(frame).convert("L").resize((hash_size + 1, hash_size))
        pixels = np.array(img, dtype=np.float32)
        diff = pixels[:, 1:] > pixels[:, :-1]
        return int(np.packbits(diff.flatten()).tobytes().hex(), 16)
    except Exception:
        return None


def hamming_distance(h1: int, h2: int) -> int:
    """Hamming distance between two perceptual hashes."""
    return bin(h1 ^ h2).count("1")


def should_skip_frame(
    current_hash: Optional[int],
    last_hash: Optional[int],
    threshold_bits: int = 5,
) -> bool:
    """Return True if the frame is too similar to the last one."""
    if current_hash is None or last_hash is None:
        return False
    return hamming_distance(current_hash, last_hash) <= threshold_bits
