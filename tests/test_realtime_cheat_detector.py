"""
Real-Time CheatDetector Test - Enhanced
========================================
Tests all detection features:
- YOLO: Faces, Phones, Books
- Gaze Estimation
- Screenshot Detection
- Tab/Copy/Paste Events
Press 'q' to quit, 't' to simulate tab switch, 'c' to simulate copy
"""
import sys
import os
import cv2
import numpy as np
import base64
import time
from datetime import datetime

sys.path.append(os.getcwd())

try:
    from backend.models.cheat_detector import CheatDetector
    print("✅ CheatDetector imported")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

def encode_frame(frame):
    _, buf = cv2.imencode('.jpg', frame)
    return base64.b64encode(buf).decode('utf-8')

def draw_overlay(frame, result):
    h, w = frame.shape[:2]
    
    # Background panel
    overlay = frame.copy()
    cv2.rectangle(overlay, (10, 10), (400, 220), (0, 0, 0), -1)
    frame = cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)
    
    # Status colors
    verdict = result.get('verdict', 'SAFE')
    if verdict == 'CRITICAL':
        color = (0, 0, 255)  # Red
    elif verdict == 'HIGH':
        color = (0, 165, 255)  # Orange
    elif verdict == 'MILD':
        color = (0, 255, 255)  # Yellow
    else:
        color = (0, 255, 0)  # Green
    
    y = 35
    
    # Verdict and score
    cv2.putText(frame, f"VERDICT: {verdict}", (20, y), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    y += 30
    
    score = result.get('suspicion_score', 0)
    cv2.putText(frame, f"Score: {score:.1f}/100", (20, y), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    y += 25
    
    confidence = result.get('confidence', 0)
    cv2.putText(frame, f"Confidence: {confidence:.0%}", (20, y), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    y += 30
    
    # Detection Status
    cv2.putText(frame, "=== DETECTIONS ===", (20, y), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    y += 22
    
    # Face count
    face_count = result.get('face_count', 0)
    face_color = (0, 255, 0) if face_count == 1 else (0, 0, 255)
    cv2.putText(frame, f"Faces: {face_count}", (20, y), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, face_color, 1)
    y += 20
    
    # Phone
    phone = result.get('phone_detected', False)
    phone_txt = "PHONE DETECTED!" if phone else "Phone: No"
    phone_color = (0, 0, 255) if phone else (0, 255, 0)
    cv2.putText(frame, phone_txt, (20, y), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, phone_color, 1)
    y += 20
    
    # Book
    book = result.get('book_detected', False)
    book_txt = "BOOK DETECTED!" if book else "Book: No"
    book_color = (0, 0, 255) if book else (0, 255, 0)
    cv2.putText(frame, book_txt, (20, y), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, book_color, 1)
    y += 20
    
    # Gaze
    looking_away = result.get('looking_away', False)
    gaze_txt = "LOOKING AWAY!" if looking_away else "Gaze: OK"
    gaze_color = (0, 165, 255) if looking_away else (0, 255, 0)
    cv2.putText(frame, gaze_txt, (20, y), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, gaze_color, 1)
    y += 20
    
    # Alert type
    alert = result.get('alert_type', 'NONE')
    if alert != 'NONE':
        cv2.putText(frame, f"ALERT: {alert}", (20, y), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    
    # Draw bounding boxes from YOLO
    details = result.get('details', {})
    yolo = details.get('yolo', {})
    
    # Draw faces/persons
    for face in yolo.get('faces', [])[:3]:
        bbox = face.get('bbox', [])
        if len(bbox) == 4:
            x1, y1, x2, y2 = map(int, bbox)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, "Face", (x1, y1-5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    
    # Draw phones
    for phone in yolo.get('phones', []):
        bbox = phone.get('bbox', [])
        if len(bbox) == 4:
            x1, y1, x2, y2 = map(int, bbox)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
            cv2.putText(frame, "PHONE!", (x1, y1-5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    
    # Draw books
    for book in yolo.get('books', []):
        bbox = book.get('bbox', [])
        if len(bbox) == 4:
            x1, y1, x2, y2 = map(int, bbox)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 165, 255), 3)
            cv2.putText(frame, "BOOK!", (x1, y1-5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
    
    # Instructions
    cv2.putText(frame, "Press 'q' to quit | 't' for tab switch | 'c' for copy", 
               (10, h-10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
    
    return frame

def main():
    print("=" * 60)
    print("    REAL-TIME CHEAT DETECTOR TEST (MediaPipe-Free)")
    print("=" * 60)
    
    detector = CheatDetector(config={'log_file': 'realtime_log.json'})
    print("✅ CheatDetector initialized")
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Webcam failed")
        return
    
    print("✅ Webcam opened")
    print("\nDETECTION GUIDE:")
    print("- Show phone to camera → PHONE_DETECTED")
    print("- Show book to camera  → BOOK_DETECTED")
    print("- Multiple people      → MULTIPLE_FACES")
    print("- Look away            → GAZE alert")
    print("- Press 't' to test tab switch")
    print("- Press 'c' to test copy detection")
    print("=" * 60)
    
    session_id = f"test_{int(time.time())}"
    frame_count = 0
    last_fps_time = time.time()
    fps = 0
    
    # Register sample questions for copy detection
    detector.register_question("What is the capital of France?")
    detector.register_question("Calculate the integral of x^2 from 0 to 1")
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            
            # Analyze every 3 frames to maintain FPS
            if frame_count % 3 == 0:
                frame_b64 = encode_frame(frame)
                result = detector.analyze_frame(frame_b64, session_id)
                
                # Log suspicious events
                if result.get('suspicious'):
                    print(f"⚠️  {datetime.now().strftime('%H:%M:%S')} | "
                          f"ALERT: {result['alert_type']} | "
                          f"Score: {result['suspicion_score']:.1f} | "
                          f"Verdict: {result['verdict']}")
                
                # Draw overlay
                frame = draw_overlay(frame, result)
            
            # Calculate FPS
            if frame_count % 15 == 0:
                now = time.time()
                fps = 15 / (now - last_fps_time)
                last_fps_time = now
            
            cv2.putText(frame, f"FPS: {fps:.1f}", (frame.shape[1]-100, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            cv2.imshow('CheatDetector - Real-Time Test', frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("\n👋 Quit")
                break
            elif key == ord('t'):
                # Simulate tab switch
                result = detector.handle_tab_switch(session_id, "Switched to Chrome")
                print(f"📑 TAB SWITCH | Score: {result['score']}")
            elif key == ord('c'):
                # Simulate copy
                result = detector.handle_copy(session_id, "What is the capital of France?")
                print(f"📋 COPY | Alert: {result['alert_type']} | Score: {result['score']}")
    
    except KeyboardInterrupt:
        print("\n👋 Interrupted")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print(f"\n✅ Complete. Frames: {frame_count}")

if __name__ == "__main__":
    main()
