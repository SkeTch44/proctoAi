"""
Advanced Proctoring Detection Engines
Implements: Head Pose, Hand Gestures, Keyboard Sounds, Behavioral Patterns, System Monitoring
"""

import numpy as np
import cv2
import logging
from typing import List, Dict, Tuple, Optional, Any
import time

logger = logging.getLogger(__name__)

# MediaPipe for Head Pose and Hands
try:
    import mediapipe as mp
    # Fix for Windows
    if not hasattr(mp, 'solutions'):
        import mediapipe.python.solutions as solutions
        mp.solutions = solutions
    mp_face_mesh = mp.solutions.face_mesh
    mp_hands = mp.solutions.hands
    mediapipe_available = True
except:
    mediapipe_available = False
    logger.warning("MediaPipe not available for advanced features")

# Audio Analysis
try:
    import librosa
    import soundfile as sf
    audio_analysis_available = True
except:
    audio_analysis_available = False
    logger.warning("Librosa not available for keyboard sound detection")

# System Monitoring
try:
    import psutil
    import pygetwindow as gw
    system_monitoring_available = True
except:
    system_monitoring_available = False
    logger.warning("System monitoring libraries not available")


# ==========================================
# 1. Head Pose Engine
# ==========================================
class HeadPoseEngine:
    """Detects head orientation to identify looking at phone/notes"""
    
    def __init__(self):
        self.face_mesh = None
        if mediapipe_available:
            try:
                self.face_mesh = mp_face_mesh.FaceMesh(
                    max_num_faces=1,
                    refine_landmarks=True,
                    min_detection_confidence=0.5,
                    min_tracking_confidence=0.5
                )
                logger.info("HeadPoseEngine initialized")
            except Exception as e:
                logger.error(f"HeadPoseEngine init failed: {e}")
    
    def estimate_head_pose(self, frame: np.ndarray) -> Dict[str, float]:
        """
        Calculate head pose angles (pitch, yaw, roll)
        Returns: {'pitch': float, 'yaw': float, 'roll': float, 'looking_down': bool}
        """
        if not self.face_mesh:
            return {'pitch': 0.0, 'yaw': 0.0, 'roll': 0.0, 'looking_down': False}
        
        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.face_mesh.process(rgb_frame)
            
            if not results.multi_face_landmarks:
                return {'pitch': 0.0, 'yaw': 0.0, 'roll': 0.0, 'looking_down': False}
            
            landmarks = results.multi_face_landmarks[0].landmark
            h, w, _ = frame.shape
            
            # Key points for pose estimation
            # Nose tip: 1, Chin: 152, Left eye: 33, Right eye: 263
            # Forehead: 10, Left ear: 234, Right ear: 454
            
            def get_3d(idx):
                return np.array([
                    landmarks[idx].x * w,
                    landmarks[idx].y * h,
                    landmarks[idx].z * w
                ])
            
            # Get key points
            nose = get_3d(1)
            chin = get_3d(152)
            forehead = get_3d(10)
            left_eye = get_3d(33)
            right_eye = get_3d(263)
            
            # Calculate pitch (up/down)
            # Negative = looking down, Positive = looking up
            face_vertical = chin - forehead
            pitch = np.arctan2(face_vertical[1], face_vertical[2]) * 180 / np.pi
            
            # Calculate yaw (left/right)
            eye_line = right_eye - left_eye
            yaw = np.arctan2(eye_line[0], eye_line[2]) * 180 / np.pi
            
            # Calculate roll (tilt)
            roll = np.arctan2(eye_line[1], eye_line[0]) * 180 / np.pi
            
            # Detect looking down (at phone/notes)
            looking_down = pitch < -15  # More than 15 degrees down
            looking_away = abs(yaw) > 35  # More than 35 degrees left/right
            
            return {
                'pitch': float(pitch),
                'yaw': float(yaw),
                'roll': float(roll),
                'looking_down': looking_down,
                'looking_away': looking_away,
                'suspicious': looking_down or looking_away
            }
            
        except Exception as e:
            logger.error(f"Head pose estimation error: {e}")
            return {'pitch': 0.0, 'yaw': 0.0, 'roll': 0.0, 'looking_down': False}


# ==========================================
# 2. Hand Gesture Engine
# ==========================================
class HandGestureEngine:
    """Detects suspicious hand gestures (phone call, writing, camera block)"""
    
    def __init__(self):
        self.hands = None
        if mediapipe_available:
            try:
                self.hands = mp_hands.Hands(
                    max_num_hands=2,
                    min_detection_confidence=0.5,
                    min_tracking_confidence=0.5
                )
                logger.info("HandGestureEngine initialized")
            except Exception as e:
                logger.error(f"HandGestureEngine init failed: {e}")
    
    def detect_gestures(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Detect hand gestures
        Returns: {'phone_call': bool, 'writing': bool, 'camera_block': bool}
        """
        if not self.hands:
            return {'phone_call': False, 'writing': False, 'camera_block': False}
        
        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(rgb_frame)
            
            if not results.multi_hand_landmarks:
                return {'phone_call': False, 'writing': False, 'camera_block': False}
            
            h, w, _ = frame.shape
            gestures = {
                'phone_call': False,
                'writing': False,
                'camera_block': False,
                'hand_count': len(results.multi_hand_landmarks)
            }
            
            for hand_landmarks in results.multi_hand_landmarks:
                # Get wrist and fingertip positions
                wrist = hand_landmarks.landmark[0]
                index_tip = hand_landmarks.landmark[8]
                
                wrist_y = wrist.y * h
                index_y = index_tip.y * h
                
                # Phone call: Hand near top of frame (near ear)
                if wrist_y < h * 0.3:  # Top 30% of frame
                    gestures['phone_call'] = True
                
                # Camera block: Hand in center of frame
                if 0.3 < wrist.y < 0.7 and 0.3 < wrist.x < 0.7:
                    gestures['camera_block'] = True
                
                # Writing: Hand in lower portion, repetitive motion
                # (Would need temporal tracking for full implementation)
                if wrist_y > h * 0.6:
                    gestures['writing'] = True
            
            return gestures
            
        except Exception as e:
            logger.error(f"Hand gesture detection error: {e}")
            return {'phone_call': False, 'writing': False, 'camera_block': False}


# ==========================================
# 3. Keyboard Sound Detector
# ==========================================
class KeyboardSoundDetector:
    """Detects typing sounds from second keyboard"""
    
    def __init__(self):
        self.enabled = audio_analysis_available
        self.keyboard_freq_range = (2000, 8000)  # Hz
        self.click_threshold = 0.3
        
    def detect_keyboard_typing(self, audio_chunk: np.ndarray, sample_rate: int = 44100) -> Dict[str, Any]:
        """
        Analyze audio for keyboard click patterns
        Returns: {'detected': bool, 'confidence': float, 'click_count': int}
        """
        if not self.enabled or len(audio_chunk) == 0:
            return {'detected': False, 'confidence': 0.0, 'click_count': 0}
        
        try:
            # Convert to frequency domain
            fft = np.fft.fft(audio_chunk)
            freqs = np.fft.fftfreq(len(audio_chunk), 1/sample_rate)
            
            # Focus on keyboard frequency range (2-8 kHz)
            mask = (freqs > self.keyboard_freq_range[0]) & (freqs < self.keyboard_freq_range[1])
            keyboard_energy = np.sum(np.abs(fft[mask]))
            
            # Normalize
            total_energy = np.sum(np.abs(fft))
            if total_energy > 0:
                keyboard_ratio = keyboard_energy / total_energy
            else:
                keyboard_ratio = 0.0
            
            # Detect clicks (sharp transients)
            # Calculate zero-crossing rate (high for clicks)
            zero_crossings = np.sum(np.abs(np.diff(np.sign(audio_chunk)))) / len(audio_chunk)
            
            # Keyboard typing has:
            # 1. High energy in 2-8kHz range
            # 2. High zero-crossing rate (sharp clicks)
            detected = keyboard_ratio > 0.3 and zero_crossings > 0.1
            confidence = min(1.0, (keyboard_ratio + zero_crossings) / 2)
            
            # Estimate click count (rough)
            click_count = int(zero_crossings * 10) if detected else 0
            
            return {
                'detected': detected,
                'confidence': float(confidence),
                'click_count': click_count,
                'keyboard_ratio': float(keyboard_ratio),
                'zero_crossings': float(zero_crossings)
            }
            
        except Exception as e:
            logger.error(f"Keyboard sound detection error: {e}")
            return {'detected': False, 'confidence': 0.0, 'click_count': 0}


# ==========================================
# 4. Behavioral Analyzer
# ==========================================
class BehavioralAnalyzer:
    """Analyzes typing and mouse patterns for anomalies"""
    
    def __init__(self):
        self.typing_history = []
        self.mouse_history = []
        self.max_history = 100
    
    def analyze_typing_pattern(self, key_intervals: List[float]) -> Dict[str, Any]:
        """
        Analyze typing intervals to detect copy-paste
        key_intervals: List of milliseconds between keystrokes
        """
        if len(key_intervals) < 10:
            return {'anomaly': False, 'type': 'INSUFFICIENT_DATA', 'confidence': 0.0}
        
        try:
            intervals = np.array(key_intervals)
            avg_interval = np.mean(intervals)
            std_interval = np.std(intervals)
            
            # Natural typing: 100-300ms average, std > 50ms
            # Copy-paste: < 20ms average, std < 10ms
            # Looking at notes: > 500ms average, high std
            
            if avg_interval < 20 and std_interval < 10:
                return {
                    'anomaly': True,
                    'type': 'PASTE_DETECTED',
                    'confidence': 0.95,
                    'avg_interval': float(avg_interval),
                    'std_interval': float(std_interval)
                }
            elif avg_interval > 500:
                return {
                    'anomaly': True,
                    'type': 'SLOW_TYPING',
                    'confidence': 0.7,
                    'reason': 'Possibly looking at notes',
                    'avg_interval': float(avg_interval)
                }
            else:
                return {
                    'anomaly': False,
                    'type': 'NORMAL_TYPING',
                    'confidence': 0.0,
                    'avg_interval': float(avg_interval),
                    'std_interval': float(std_interval)
                }
                
        except Exception as e:
            logger.error(f"Typing pattern analysis error: {e}")
            return {'anomaly': False, 'type': 'ERROR', 'confidence': 0.0}
    
    def analyze_mouse_activity(self, mouse_events: List[Dict]) -> Dict[str, Any]:
        """
        Analyze mouse movement patterns
        mouse_events: [{'x': int, 'y': int, 'timestamp': float}]
        """
        if len(mouse_events) < 5:
            return {'anomaly': False, 'type': 'INSUFFICIENT_DATA'}
        
        try:
            # Check for inactivity
            time_span = mouse_events[-1]['timestamp'] - mouse_events[0]['timestamp']
            if time_span > 30:  # 30 seconds of inactivity
                return {
                    'anomaly': True,
                    'type': 'MOUSE_INACTIVE',
                    'confidence': 0.6,
                    'inactive_duration': time_span
                }
            
            # Calculate movement speed
            distances = []
            for i in range(1, len(mouse_events)):
                dx = mouse_events[i]['x'] - mouse_events[i-1]['x']
                dy = mouse_events[i]['y'] - mouse_events[i-1]['y']
                dist = np.sqrt(dx**2 + dy**2)
                distances.append(dist)
            
            avg_speed = np.mean(distances) if distances else 0
            
            # Very slow movement might indicate looking away
            if avg_speed < 5:
                return {
                    'anomaly': True,
                    'type': 'SLOW_MOUSE',
                    'confidence': 0.4,
                    'avg_speed': float(avg_speed)
                }
            
            return {'anomaly': False, 'type': 'NORMAL', 'avg_speed': float(avg_speed)}
            
        except Exception as e:
            logger.error(f"Mouse activity analysis error: {e}")
            return {'anomaly': False, 'type': 'ERROR'}


# ==========================================
# 5. System Monitor
# ==========================================
class SystemMonitor:
    """Monitors system for suspicious processes and configurations"""
    
    def __init__(self):
        self.enabled = system_monitoring_available
        self.suspicious_processes = [
            'obs64.exe', 'obs32.exe', 'obs.exe',  # OBS Studio
            'teamviewer.exe',  # Remote access
            'anydesk.exe',  # Remote access
            'discord.exe',  # Communication
            'telegram.exe',  # Communication
            'zoom.exe',  # Communication
            'skype.exe',  # Communication
        ]
    
    def check_suspicious_processes(self) -> Dict[str, Any]:
        """Check for suspicious running processes"""
        if not self.enabled:
            return {'detected': False, 'processes': []}
        
        try:
            found_processes = []
            for proc in psutil.process_iter(['name']):
                try:
                    proc_name = proc.info['name'].lower()
                    if proc_name in self.suspicious_processes:
                        found_processes.append(proc_name)
                except:
                    continue
            
            return {
                'detected': len(found_processes) > 0,
                'processes': found_processes,
                'count': len(found_processes)
            }
            
        except Exception as e:
            logger.error(f"Process monitoring error: {e}")
            return {'detected': False, 'processes': []}
    
    def detect_multiple_monitors(self) -> Dict[str, Any]:
        """Detect if multiple monitors are connected"""
        if not self.enabled:
            return {'multiple_monitors': False, 'count': 1}
        
        try:
            # This is a simplified check
            # More accurate detection would require platform-specific APIs
            import screeninfo
            screens = screeninfo.get_monitors()
            
            return {
                'multiple_monitors': len(screens) > 1,
                'count': len(screens),
                'screens': [{'width': s.width, 'height': s.height} for s in screens]
            }
        except:
            # Fallback method
            try:
                windows = gw.getAllWindows()
                # Heuristic: If windows span beyond typical single monitor width
                max_x = max([w.left + w.width for w in windows] + [1920])
                return {
                    'multiple_monitors': max_x > 2000,
                    'count': 2 if max_x > 2000 else 1
                }
            except:
                return {'multiple_monitors': False, 'count': 1}
    
    def get_network_stats(self) -> Dict[str, Any]:
        """Get current network usage statistics"""
        if not self.enabled:
            return {'bytes_sent': 0, 'bytes_recv': 0, 'spike': False}
        
        try:
            net_io = psutil.net_io_counters()
            return {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv,
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv
            }
        except Exception as e:
            logger.error(f"Network stats error: {e}")
            return {'bytes_sent': 0, 'bytes_recv': 0}
