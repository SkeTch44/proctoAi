
import cv2
import base64
import time
import json
import logging
import sys
import os
import numpy as np
import threading
import sounddevice as sd

sys.path.append(os.getcwd())

# Disable non-error logging
logging.getLogger("backend.models.cheat_detector").setLevel(logging.ERROR)
logging.getLogger("ultralytics").setLevel(logging.ERROR)

from backend.models.cheat_detector import CheatDetector

# Audio Config
SAMPLE_RATE = 44100
CHANNELS = 1
BLOCK_SIZE = 4096

detector = None
audio_alert = None

def audio_callback(indata, frames, time, status):
    global detector, audio_alert
    if status:
        print(f"Audio Status: {status}")
    if detector:
        # Convert int16 bytes
        # sd returns float32 by default? Let's assume float32 and convert to int16 bytes for API compat
        # Or just use raw bytes if API expects them.
        # VisionEngine.AudioEngine expects base64 of int16 buffer.
        
        # Convert float32 -> int16
        audio_int16 = (indata * 32767).astype(np.int16)
        audio_bytes = audio_int16.tobytes()
        b64_audio = base64.b64encode(audio_bytes).decode('utf-8')
        
        res = detector.analyze_audio(b64_audio, "demo_session")
        if res.get('suspicious'):
            audio_alert = f"AUDIO SPIKE: {res['details']['db']:.1f} dB"
        else:
            audio_alert = None # Clear if quiet

def run_demo():
    global detector, audio_alert
    print("=====================================================")
    print("      AI PROCTOR: LIVE CHEAT DEMO v2 (Audio+Gaze)    ")
    print("=====================================================")
    
    # Init
    try:
        detector = CheatDetector(config={'enable_emotion_analysis': False}) 
        print("Engine Initialized.")
    except Exception as e:
        print(f"Init Failed: {e}")
        return

    # Start Mic
    try:
        stream = sd.InputStream(
            channels=CHANNELS, 
            samplerate=SAMPLE_RATE, 
            blocksize=BLOCK_SIZE, 
            callback=audio_callback
        )
        stream.start()
        print("Microphone Active.")
    except Exception as e:
        print(f"Microphone failed: {e}")

    # Webcam
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Webcam failed.")
        return

    print(">>> Controls: 'q' Quit, 's' Screenshot, 't' Tab Switch")

    while True:
        ret, frame = cap.read()
        if not ret: break

        # Encode
        _, buffer = cv2.imencode('.jpg', frame)
        b64_frame = "data:image/jpeg;base64," + base64.b64encode(buffer).decode('utf-8')
        
    def detect_objects(self, frame: np.ndarray, target_classes: List[str]) -> List[Dict]:
    """Detect suspicious objects (phone, book, laptop)"""
    if not self.enabled or self.model is None:
        return []
    
    COCO_CLASSES = {67: 'cell phone', 73: 'book', 63: 'laptop'}
    target_ids = [cid for cid, name in COCO_CLASSES.items() if name in target_classes]
    
    if not target_ids:
        return []
    
    try:
        results = self.model(frame, classes=target_ids, verbose=False)
        objects = []
        for r in results:
            for box in r.boxes:
                cls = int(box.cls[0])
                if cls in COCO_CLASSES:
                    objects.append({
                        'class': COCO_CLASSES[cls],
                        'box': box.xyxy[0].tolist(),
                        'conf': float(box.conf[0])
                    })
        return objects
    except Exception as e:
        logger.error(f"Object detection error: {e}")
        return []    

        # Analyze Vision
        res = detector.analyze_frame(b64_frame, "demo_session")
        
        # Visualize
        suspicious = res['suspicious']
        score = res['suspicion_score']
        alert = res['alert_type']
        details = res.get('details', {})
        
        # Default Color
        color = (0, 255, 0)
        
        # Draw Faces
        screen_center = None
        face_center = None
        
        for i, face in enumerate(details.get('face_locations', [])):
            x1, y1, x2, y2 = map(int, face['box'])
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 0), 2)
            
            # Calculate face center for first face
            if i == 0:
                face_center = (int((x1 + x2) / 2), int((y1 + y2) / 2))
        
        # Draw screen center and drift line
        h, w, _ = frame.shape
        screen_center = (w // 2, h // 2)
        
        # Screen center marker (green crosshair)
        cv2.drawMarker(frame, screen_center, (0, 255, 0), cv2.MARKER_CROSS, 20, 2)
        
        # Face center and drift line
        if face_center:
            cv2.circle(frame, face_center, 5, (0, 165, 255), -1)
            cv2.line(frame, screen_center, face_center, (255, 0, 255), 2)
            
            # Calculate drift distance
            dx = abs(face_center[0] - screen_center[0]) / w
            dy = abs(face_center[1] - screen_center[1]) / h
            drift = np.sqrt(dx**2 + dy**2)
            cv2.putText(frame, f"Drift: {drift:.2f}", 
                       (face_center[0] + 10, face_center[1]), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 2)
        
        # Alert Overlays
        y = 30
        
        # 1. Main Visual Alert
        if suspicious:
            color = (0, 0, 255)
            cv2.putText(frame, f"ALERT: {alert}", (10, y), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 3)
            y += 40
        else:
            cv2.putText(frame, "STATUS: CLEAN", (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            y += 40
            
        # 2. Score
        cv2.putText(frame, f"SCORE: {score:.1f}", (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        y += 30
        
        # 3. Smoothing Info
        raw_scores = details.get('raw_scores', {})
        smoothed_scores = details.get('smoothed_scores', {})
        trends = details.get('temporal_trends', {})
        
        # Show raw vs smoothed for gaze
        gaze_raw = raw_scores.get('gaze_aversion', 0)
        gaze_smooth = smoothed_scores.get('gaze_aversion', 0)
        gaze_trend = trends.get('gaze_aversion', 'stable')
        
        cv2.putText(frame, f"Gaze: Raw={gaze_raw:.0f} Smooth={gaze_smooth:.0f} [{gaze_trend}]", 
                   (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        if gaze_smooth > 50:
             cv2.putText(frame, "LOOKING AWAY", (450, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        y += 25

        # 4. Audio Alert overlay
        if audio_alert:
            cv2.putText(frame, audio_alert, (10, 400), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 3)

        cv2.imshow('AI Proctor Demo v2', frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'): break
        elif key == ord('s'): detector.handle_screenshot("demo")
        elif key == ord('t'): detector.handle_tab_switch("demo")

    stream.stop()
    stream.close()
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_demo()
