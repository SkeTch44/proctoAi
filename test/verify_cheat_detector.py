
import logging
import sys
import os
import base64
import numpy as np
import cv2
import json

# Setup path
sys.path.append(os.getcwd())

# Configure Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VERIFY_CHEAT")

from backend.models.cheat_detector import CheatDetector

def create_blank_image_b64():
    # Create black image 480x640
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    _, buffer = cv2.imencode('.jpg', img)
    b64_str = base64.b64encode(buffer).decode('utf-8')
    return f"data:image/jpeg;base64,{b64_str}"

def create_noise_audio_b64():
    # Create random noise (high volume)
    # 44100Hz 1 sec
    noise = np.random.uniform(-30000, 30000, 44100).astype(np.int16)
    b64_str = base64.b64encode(noise.tobytes()).decode('utf-8')
    return b64_str

def run_verification():
    logger.info(">>> Initializing CheatDetector...")
    detector = CheatDetector()
    
    # 1. Test Frame Analysis (Blank Image -> Face Absence)
    logger.info("\n>>> Testing Frame Analysis (Expected: FACE_ABSENCE)")
    b64_img = create_blank_image_b64()
    result = detector.analyze_frame(b64_img, session_id="test_sess_001")
    
    print(json.dumps(result, indent=2))
    
    if result.get('suspicious') and result.get('alert_type') == 'FACE_ABSENCE':
        logger.info("✅ Face Absence Detected Correctly")
    else:
        logger.error("❌ Face Absence Failed")

    # 2. Test Audio Analysis (Noise -> High Volume)
    logger.info("\n>>> Testing Audio Analysis (Expected: HIGH_VOLUME)")
    b64_audio = create_noise_audio_b64()
    res_audio = detector.analyze_audio(b64_audio, session_id="test_sess_001")
    
    print(json.dumps(res_audio, indent=2))
    
    if res_audio.get('suspicious'):
        logger.info("✅ High Volume Detected Correctly")
    else:
        logger.error("❌ Audio Check Failed")

if __name__ == "__main__":
    run_verification()
