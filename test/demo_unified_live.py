"""
Real-Time Unified CheatDetector Demo (Simplified)
Tests visual features: Face, Head Pose, Hand Gestures, Objects, Certainty
"""

import cv2
import base64
import time
import logging
import sys
import os
import numpy as np
from collections import deque

sys.path.append(os.getcwd())

# Disable non-error logging
logging.getLogger("backend.models.cheat_detector").setLevel(logging.ERROR)
logging.getLogger("ultralytics").setLevel(logging.ERROR)
logging.getLogger("mediapipe").setLevel(logging.ERROR)

from backend.models.cheat_detector import CheatDetector

# Global state
detector = None
system_violations = []

def draw_hud(frame, result, fps):
    """Draw comprehensive HUD with all detection info"""
    h, w = frame.shape[:2]
    
    # Semi-transparent overlay
    overlay = frame.copy()
    
    # Top bar - Status
    status_color = (0, 0, 255) if result.get('suspicious') else (0, 255, 0)
    cv2.rectangle(overlay, (0, 0), (w, 60), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
    
    status_text = f"STATUS: {'⚠️ VIOLATION' if result.get('suspicious') else '✓ NORMAL'}"
    cv2.putText(frame, status_text, (10, 35), cv2.FONT_HERSHEY_DUPLEX, 1.0, status_color, 3)
    
    score = result.get('suspicion_score', 0)
    severity = result.get('severity', 'LOW')
    cv2.putText(frame, f"Score: {score:.1f} | {severity}", (w-300, 35), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # FPS
    cv2.putText(frame, f"FPS: {fps:.1f}", (w-120, h-10), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    # Left panel - Core Detections
    y_offset = 80
    cv2.putText(frame, "CORE DETECTIONS:", (10, y_offset), 
                cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 0), 2)
    y_offset += 25
    
    details = result.get('details', {})
    faces = details.get('faces_detected', 0)
    smoothed = details.get('smoothed_scores', {})
    
    # Face status
    face_color = (0, 255, 0) if faces == 1 else (0, 0, 255)
    face_text = f"Faces: {faces} {'✓' if faces == 1 else '✗'}"
    cv2.putText(frame, face_text, (10, y_offset), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, face_color, 2)
    y_offset += 25
    
    # Gaze
    gaze = smoothed.get('gaze_aversion', 0)
    gaze_color = (0, 255, 0) if gaze < 30 else (0, 165, 255) if gaze < 60 else (0, 0, 255)
    gaze_text = f"Gaze: {gaze:.0f}% {'✓' if gaze < 30 else '⚠' if gaze < 60 else '✗'}"
    cv2.putText(frame, gaze_text, (10, y_offset), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, gaze_color, 2)
    y_offset += 30
    
    # Advanced Detections
    advanced = details.get('advanced', {})
    if advanced:
        cv2.putText(frame, "ADVANCED DETECTIONS:", (10, y_offset), 
                    cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 0), 2)
        y_offset += 25
        
        # Head Pose
        head_pose = advanced.get('head_pose', {})
        if head_pose:
            pitch = head_pose.get('pitch', 0)
            yaw = head_pose.get('yaw', 0)
            looking_down = head_pose.get('looking_down', False)
            looking_away = head_pose.get('looking_away', False)
            
            if looking_down:
                head_status = "📱 LOOKING DOWN!"
                head_color = (0, 0, 255)
            elif looking_away:
                head_status = "👀 LOOKING AWAY!"
                head_color = (0, 165, 255)
            else:
                head_status = "✓ Focused"
                head_color = (0, 255, 0)
            
            cv2.putText(frame, f"Head: {head_status}", (10, y_offset), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, head_color, 2)
            y_offset += 18
            cv2.putText(frame, f"  Pitch: {pitch:.0f}° | Yaw: {yaw:.0f}°", (10, y_offset), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
            y_offset += 25
        
        # Hand Gestures
        gestures = advanced.get('hand_gestures', {})
        if gestures:
            phone_call = gestures.get('phone_call', False)
            camera_block = gestures.get('camera_block', False)
            hand_count = gestures.get('hand_count', 0)
            
            if phone_call:
                cv2.putText(frame, "Hands: 📞 PHONE CALL!", (10, y_offset), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            elif camera_block:
                cv2.putText(frame, "Hands: 🚫 BLOCKING CAM", (10, y_offset), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 2)
            else:
                cv2.putText(frame, f"Hands: ✓ OK ({hand_count} detected)", (10, y_offset), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            y_offset += 30
    
    # Objects Detected
    objects = details.get('suspicious_objects', [])
    if objects:
        cv2.putText(frame, "⚠️ OBJECTS DETECTED:", (10, y_offset), 
                    cv2.FONT_HERSHEY_DUPLEX, 0.6, (0, 0, 255), 2)
        y_offset += 20
        for obj in objects[:3]:  # Show max 3
            obj_icon = "📱" if obj['class'] == 'cell phone' else "📚" if obj['class'] == 'book' else "💻"
            cv2.putText(frame, f"  {obj_icon} {obj['class']} ({obj['conf']:.0%})", (10, y_offset), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 2)
            y_offset += 18
    
    # Right panel - Certainty & Evidence
    y_offset = 80
    certainty = details.get('certainty', {})
    if certainty:
        cv2.putText(frame, "CERTAINTY ANALYSIS:", (w-280, y_offset), 
                    cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 0), 2)
        y_offset += 25
        
        cert_score = certainty.get('certainty_score', 0)
        verdict = certainty.get('verdict', 'Unknown')
        level = certainty.get('certainty_level', 'LOW')
        
        cert_color = (0, 0, 255) if level in ['VERY_HIGH', 'HIGH'] else (0, 165, 255) if level == 'MEDIUM' else (0, 255, 0)
        
        cv2.putText(frame, f"{cert_score:.0f}% - {level}", (w-280, y_offset), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, cert_color, 2)
        y_offset += 22
        cv2.putText(frame, verdict, (w-280, y_offset), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, cert_color, 2)
        y_offset += 30
        
        # Evidence
        evidence = certainty.get('evidence', [])
        if evidence:
            cv2.putText(frame, "Evidence:", (w-280, y_offset), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
            y_offset += 18
            for ev in evidence[:4]:  # Show max 4
                # Truncate long evidence
                ev_text = ev[:35] + "..." if len(ev) > 35 else ev
                cv2.putText(frame, f"• {ev_text}", (w-280, y_offset), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200), 1)
                y_offset += 14
    
    # Draw face boxes
    face_locs = details.get('face_locations', [])
    for face in face_locs:
        box = face['box']
        x1, y1, x2, y2 = map(int, box)
        color = (0, 255, 0) if len(face_locs) == 1 else (0, 0, 255)
        thickness = 2 if len(face_locs) == 1 else 3
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
        cv2.putText(frame, f"{face['conf']:.0%}", (x1, y1-10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    
    # Draw object boxes
    for obj in objects:
        box = obj['box']
        x1, y1, x2, y2 = map(int, box)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
        label = f"{obj['class']} {obj['conf']:.0%}"
        cv2.putText(frame, label, (x1, y1-10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    
    # Controls (bottom left)
    controls = [
        "CONTROLS:",
        "S - Screenshot Event",
        "T - Tab Switch Event",
        "C - Copy/Paste Event",
        "Q - Quit Demo"
    ]
    y_offset = h - 110
    for ctrl in controls:
        cv2.putText(frame, ctrl, (10, y_offset), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        y_offset += 18

def run_demo():
    global detector
    
    print("=" * 70)
    print(" " * 15 + "UNIFIED CHEAT DETECTOR - LIVE DEMO")
    print("=" * 70)
    print("\n🚀 Initializing Unified CheatDetector...")
    
    # Initialize detector with advanced features
    detector = CheatDetector(config={
        'enable_advanced': True,
        'temporal_window': 10,
        'smoothing_alpha': 0.3
    })
    
    print("✅ Detector initialized (Core + Advanced)")
    print("\n📋 Active Features:")
    print("   ✓ Face Detection (YOLO)")
    print("   ✓ Gaze Tracking (BBox Drift)")
    print("   ✓ Head Pose Analysis (MediaPipe)")
    print("   ✓ Hand Gesture Recognition (MediaPipe)")
    print("   ✓ Object Detection (Phone, Book, Laptop)")
    print("   ✓ Temporal Smoothing (EMA)")
    print("   ✓ Certainty Engine (Cheating Probability)")
    
    # Open webcam
    print("\n📹 Opening webcam...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Failed to open webcam")
        return
    
    # Set resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    print("✅ Webcam active")
    print("\n" + "=" * 70)
    print(" " * 20 + "🎥 DEMO RUNNING")
    print("=" * 70)
    print("\n💡 Tips:")
    print("   • Look down to trigger head pose detection")
    print("   • Hold hand near ear to simulate phone call")
    print("   • Show phone/book to camera for object detection")
    print("   • Press S/T/C to simulate events")
    print("\n" + "=" * 70 + "\n")
    
    fps_counter = deque(maxlen=30)
    last_time = time.time()
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ Failed to read frame")
            break
        
        frame_count += 1
        
        # Calculate FPS
        current_time = time.time()
        fps = 1 / (current_time - last_time) if (current_time - last_time) > 0 else 0
        fps_counter.append(fps)
        avg_fps = np.mean(fps_counter)
        last_time = current_time
        
        # Analyze every frame
        try:
            # Encode frame
            _, buffer = cv2.imencode('.jpg', frame)
            b64_frame = base64.b64encode(buffer).decode('utf-8')
            frame_data = f"data:image/jpeg;base64,{b64_frame}"
            
            # Analyze
            result = detector.analyze_frame(frame_data, "demo_session")
            
            # Print alerts
            if result.get('suspicious') and frame_count % 30 == 0:  # Every second at 30fps
                alert = result.get('alert_type', 'UNKNOWN')
                score = result.get('suspicion_score', 0)
                print(f"⚠️  ALERT: {alert} (Score: {score:.1f})")
            
        except Exception as e:
            print(f"❌ Analysis error: {e}")
            result = {'suspicious': False, 'suspicion_score': 0, 'severity': 'LOW', 'details': {}}
        
        # Draw HUD
        draw_hud(frame, result, avg_fps)
        
        # Display
        cv2.imshow('Unified CheatDetector - Live Demo', frame)
        
        # Handle keys
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            print("\n🛑 Quit requested")
            break
        elif key == ord('s'):
            print("📸 Screenshot event triggered!")
            detector.handle_screenshot("demo_session")
        elif key == ord('t'):
            print("🔄 Tab switch event triggered!")
            detector.handle_tab_switch("demo_session")
        elif key == ord('c'):
            print("📋 Copy/Paste event triggered!")
            detector.handle_copy_paste("demo_session", "sample text")
    
    # Cleanup
    print("\n" + "=" * 70)
    print("🔄 Shutting down...")
    cap.release()
    cv2.destroyAllWindows()
    print("✅ Demo ended successfully")
    print("=" * 70)

if __name__ == "__main__":
    try:
        run_demo()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user (Ctrl+C)")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
