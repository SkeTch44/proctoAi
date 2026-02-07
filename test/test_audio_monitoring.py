import unittest
import sys
import os
import base64
import numpy as np

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from models.cheat_detector import CheatDetector

class TestAudioMonitoring(unittest.TestCase):
    def setUp(self):
        self.detector = CheatDetector()
        
    def generate_audio_chunk(self, amplitude, duration_sec=1.0, sample_rate=44100):
        """Generate a base64 encoded PCM audio chunk"""
        t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), False)
        # Generate sine wave
        audio_data = amplitude * np.sin(2 * np.pi * 440 * t)
        # Convert to 16-bit integers
        audio_ints = audio_data.astype(np.int16)
        # Bytes
        audio_bytes = audio_ints.tobytes()
        # Base64 encode
        return base64.b64encode(audio_bytes).decode('utf-8')

    def test_silence(self):
        """Test that silence returns no suspicion"""
        # Amplitude 0
        audio_b64 = self.generate_audio_chunk(0)
        result = self.detector.analyze_audio(audio_b64, session_id="test_silence")
        
        self.assertFalse(result['suspicious'])
        self.assertEqual(result['suspicion_score'], 0)
        print(f"\nSilence Test: dB={result['details'].get('decibels')}, Suspicious={result['suspicious']}")

    def test_quiet_noise(self):
        """Test that low noise (below threshold) is ignored"""
        # Amplitude 1000 (out of 32768) => ~60dB relative to 1? 
        # 20*log10(1000) = 60dB.. wait.
        # My detector uses pure value. 
        # Threshold is 60.
        # 20*log10(1000) = 60.
        # Let's try amplitude 500 => 54 dB.
        audio_b64 = self.generate_audio_chunk(500)
        result = self.detector.analyze_audio(audio_b64, session_id="test_quiet")
        
        self.assertFalse(result['suspicious'])
        print(f"Quiet Test: dB={result['details'].get('decibels')}, Suspicious={result['suspicious']}")

    def test_loud_noise(self):
        """Test that loud noise triggers suspicion"""
        # Amplitude 10000 => 80 dB
        audio_b64 = self.generate_audio_chunk(10000)
        result = self.detector.analyze_audio(audio_b64, session_id="test_loud")
        
        self.assertTrue(result['suspicious'])
        self.assertEqual(result['alert_type'], 'HIGH_VOLUME_DETECTED')
        print(f"Loud Test: dB={result['details'].get('decibels')}, Suspicious={result['suspicious']}")

if __name__ == '__main__':
    unittest.main()
