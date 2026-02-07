
import unittest
import base64
import numpy as np
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from models.cheat_detector import CheatDetector

class TestAudioAnalysis(unittest.TestCase):
    def setUp(self):
        self.detector = CheatDetector()
        
    def test_quiet_audio(self):
        """Test that quiet audio returns low suspicion"""
        # Generate 1 second of silence (zeros)
        # 16-bit PCM, 16000 Hz, 1 channel
        audio_data = np.zeros(16000, dtype=np.int16).tobytes()
        b64_audio = base64.b64encode(audio_data).decode('utf-8')
        
        result = self.detector.analyze_audio(b64_audio)
        self.assertFalse(result['suspicious'])
        self.assertEqual(result['suspicion_score'], 0)
        
    def test_loud_audio(self):
        """Test that loud audio triggers suspicion"""
        # Generate 1 second of loud noise (max amplitude)
        # Random noise close to int16 limits
        audio_data = np.random.randint(-30000, 30000, 16000, dtype=np.int16).tobytes()
        b64_audio = base64.b64encode(audio_data).decode('utf-8')
        
        result = self.detector.analyze_audio(b64_audio)
        
        # Depending on random generation, it should be loud enough > 60dB
        # We might need to force it to be consistently loud
        # Let's use constant max amplitude
        audio_data = np.full(16000, 30000, dtype=np.int16).tobytes()
        b64_audio = base64.b64encode(audio_data).decode('utf-8')
        
        result = self.detector.analyze_audio(b64_audio)
        self.assertTrue(result['suspicious'])
        self.assertEqual(result['severity'], 'MEDIUM') # Based on logic
        self.assertEqual(result['alert_type'], 'HIGH_VOLUME_DETECTED')

if __name__ == '__main__':
    unittest.main()
