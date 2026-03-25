
import sys
import os
import base64
import numpy as np
import cv2
import json
from pprint import pprint

# Ensure we can import backend modules
sys.path.append(os.getcwd())

try:
    from backend.models.cheat_detector import CheatDetector
except ImportError as e:
    print(f"Failed to import CheatDetector: {e}")
    sys.exit(1)

def create_mock_frame():
    # Create a blank black image
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    # Encode to jpg then base64
    _, buffer = cv2.imencode('.jpg', img)
    jpg_as_text = base64.b64encode(buffer).decode('utf-8')
    return jpg_as_text

def run_verification():
    print("🚀 Initializing Unified CheatDetector...")
    try:
        detector = CheatDetector(config={'enable_advanced': True, 'log_file': 'test_log.json'})
        print("✅ Initialization successful")
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return

    session_id = "test_session_123"

    # 1. Test analyze_frame (Core + Init Check)
    print("\n📸 Testing analyze_frame...")
    try:
        mock_frame = create_mock_frame()
        result = detector.analyze_frame(mock_frame, session_id)
        pprint(result)
        if 'suspicion_score' in result:
            print("✅ analyze_frame passed")
        else:
            print("❌ analyze_frame returned unexpected structure")
    except Exception as e:
        print(f"❌ analyze_frame failed: {e}")

    # 2. Test analyze_audio_advanced
    print("\n🎤 Testing analyze_audio_advanced...")
    try:
        # 1 second of silence
        mock_audio = np.zeros(44100, dtype=np.float32)
        result = detector.analyze_audio_advanced(mock_audio, session_id)
        pprint(result)
        if 'keyboard_detected' in result:
            print("✅ analyze_audio_advanced passed")
        else:
            print("❌ analyze_audio_advanced missing 'keyboard_detected'")
    except Exception as e:
        print(f"❌ analyze_audio_advanced failed: {e}")

    # 3. Test analyze_typing_pattern
    print("\n⌨️ Testing analyze_typing_pattern (Simulated Paste)...")
    try:
        # Simulate paste content (very fast typing)
        mock_intervals = [5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5]
        result = detector.analyze_typing_pattern(mock_intervals, session_id)
        pprint(result)
        if result.get('type') == 'PASTE_DETECTED':
            print("✅ analyze_typing_pattern detected paste correctly")
        else:
             print(f"⚠️ analyze_typing_pattern output unexpected: {result.get('type')}")
    except Exception as e:
        print(f"❌ analyze_typing_pattern failed: {e}")

    # 4. Test analyze_mouse_activity
    print("\n🖱️ Testing analyze_mouse_activity...")
    try:
        mock_events = [{'x': 0, 'y': 0, 'timestamp': 100}, {'x': 10, 'y': 10, 'timestamp': 101}]
        result = detector.analyze_mouse_activity(mock_events, session_id)
        pprint(result)
        print("✅ analyze_mouse_activity passed")
    except Exception as e:
        print(f"❌ analyze_mouse_activity failed: {e}")

    # 5. Test check_system_status
    print("\n💻 Testing check_system_status...")
    try:
        result = detector.check_system_status(session_id)
        pprint(result)
        print("✅ check_system_status passed")
    except Exception as e:
        print(f"❌ check_system_status failed: {e}")
        
    # 6. Test Object Detection (YOLOv8)
    print("\n🔍 Testing Object Detection (YOLOv8)...")
    try:
        # Create a mock frame (YOLO might not find anything on black, but execution shouldn't crash)
        # To actually verify detection, we'd need a real image, but here we verify integration.
        mock_frame_obj = create_mock_frame()
        result_obj = detector.analyze_frame(mock_frame_obj, session_id)
        
        objects = result_obj.get('details', {}).get('advanced', {}).get('objects', {})
        pprint(objects)
        
        if 'found' in objects:
            print("✅ Object detection ran successfully")
        else:
             print("❌ Object detection output missing 'found' key")
    except Exception as e:
        print(f"❌ Object detection failed: {e}")

    # 7. Test Event Handlers
    print("\n🔔 Testing Event Handlers...")
    try:
        res1 = detector.handle_tab_switch(session_id)
        print(f"Tab Switch: {res1['alert_type']}")
        
        res2 = detector.handle_copy_paste(session_id, "copied text")
        print(f"Copy Paste: {res2['alert_type']}")
        
        if res1['suspicious'] and res2['suspicious']:
            print("✅ Event handlers passed")
        else:
            print("❌ Event handlers failed logic")
    except Exception as e:
        print(f"❌ Event handlers failed: {e}")
        
    print("\n✨ Verification Complete")

if __name__ == "__main__":
    run_verification()
