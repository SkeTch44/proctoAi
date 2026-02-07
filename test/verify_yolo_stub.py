
import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import json
import base64
import numpy as np
import cv2

sys.path.append(os.getcwd())

# Mock Ultralytics BEFORE importing cheat_detector
sys.modules['ultralytics'] = MagicMock()
sys.modules['deepface'] = MagicMock()

from backend.models.cheat_detector import CheatDetector

class TestYOLOCheatDetector(unittest.TestCase):
    def setUp(self):
        self.detector = CheatDetector()
        
        # Mock YOLO model response
        self.detector.vision.model = MagicMock()
        self.detector.vision.enabled = True
        
    def create_mock_frame(self):
        # Create valid base64 image
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        _, buf = cv2.imencode('.jpg', img)
        return "data:image/jpeg;base64," + base64.b64encode(buf).decode('utf-8')

    def test_face_absence(self):
        print("\n>>> Testing Face Absence (0 persons)")
        # Mock YOLO return: 0 boxes
        mock_result = MagicMock()
        mock_result.boxes = []
        self.detector.vision.model.return_value = [mock_result]
        
        res = self.detector.analyze_frame(self.create_mock_frame(), "sess_1")
        print(f"Result: {res['alert_type']}")
        
        self.assertEqual(res['alert_type'], 'FACE_ABSENCE')
        self.assertTrue(res['suspicious'])

    def test_multiple_faces(self):
        print("\n>>> Testing Multiple Faces (2 persons)")
        # Mock YOLO return: 2 boxes, class 0
        mock_box = MagicMock()
        mock_box.xyxy = [np.array([0,0,50,50])]
        mock_box.conf = [0.9]
        
        mock_result = MagicMock()
        mock_result.boxes = [mock_box, mock_box] # 2 faces
        self.detector.vision.model.return_value = [mock_result]
        
        res = self.detector.analyze_frame(self.create_mock_frame(), "sess_1")
        print(f"Result: {res['alert_type']}")
        
        self.assertEqual(res['alert_type'], 'MULTIPLE_FACES')

    def test_audio_spike(self):
        print("\n>>> Testing Audio Spike")
        noise = np.random.uniform(-30000, 30000, 1000).astype(np.int16)
        b64 = base64.b64encode(noise.tobytes()).decode('utf-8')
        res = self.detector.analyze_audio(b64, "sess_1")
        self.assertEqual(res['alert_type'], 'HIGH_VOLUME_DETECTED')

    def test_screenshot(self):
        print("\n>>> Testing Screenshot")
        res = self.detector.handle_screenshot("sess_1")
        print(f"Result: {res['alert_type']} (Score: {res['suspicion_score']})")
        self.assertEqual(res['alert_type'], 'SCREENSHOT_ATTEMPT')
        self.assertEqual(res['suspicion_score'], 100.0)

    def test_copy_paste(self):
        print("\n>>> Testing Copy/Paste")
        res = self.detector.handle_copy_paste("sess_1", "Some copied text")
        print(f"Result: {res['alert_type']} (Score: {res['suspicion_score']})")
        self.assertEqual(res['alert_type'], 'COPY_PASTE_DETECTED')

if __name__ == '__main__':
    unittest.main()
