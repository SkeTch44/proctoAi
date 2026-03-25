"""
Unified CheatDetector - MediaPipe-Free Implementation
======================================================
All detection using:
- YOLO for faces, phones, books
- OpenCV for gaze estimation
- PIL/mss for screenshot detection
- Browser events for tab/copy detection
"""

import base64
import json
import logging 
from typing import Dict, Any, Optional, List
from datetime import datetime
from collections import deque
import os
import time
import math
import threading

logger = logging.getLogger(__name__)

# ==========================================
# Feature Availability Checks
# ==========================================

try:
    import cv2
    cv2_available = True
except ImportError:
    cv2_available = False
    logger.warning("OpenCV not available")

try:
    import numpy as np
    numpy_available = True
except ImportError:
    numpy_available = False
    logger.warning("NumPy not available")

# ultralytics_available check moved to YOLODetector
ultralytics_available = False # Placeholder, handled in init

try:
    import psutil
    psutil_available = True
except ImportError:
    psutil_available = False

try:
    import pyautogui
    pyautogui_available = True
except ImportError:
    pyautogui_available = False
    logger.warning("PyAutoGUI not available - screenshot detection limited")

try:
    from PIL import ImageGrab
    pil_available = True
except ImportError:
    pil_available = False

# Mesa ABM
# MesaService import moved to lazy property
mesa_available = True # Check performed in property


# ==========================================
# 1. YOLO-BASED DETECTOR (Face, Phone, Book)
# ==========================================
class YOLODetector:
    """
    YOLOv8 for detecting:
    - Faces (class 0 in yolov8n-face or use person class)
    - Cell phones (class 67)
    - Books (class 73)
    - Multiple people detection
    """
    
    # COCO class IDs
    CLASS_PERSON = 0
    CLASS_PHONE = 67
    CLASS_BOOK = 73
    
    def __init__(self):
        self.model = None
        self.face_cascade = None
        
        try:
            from ultralytics import YOLO
            self.model = YOLO("yolov8n.pt")
            logging.getLogger("ultralytics").setLevel(logging.WARNING)
            logger.info("YOLO model loaded successfully")
        except ImportError:
            logger.warning("YOLOv8 not available")
        except Exception as e:
            logger.warning(f"Failed to load YOLO: {e}")
        
        # Fallback: OpenCV Haar Cascade for face detection
        if cv2_available:
            try:
                cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                self.face_cascade = cv2.CascadeClassifier(cascade_path)
            except:
                pass
    
    def detect(self, frame: np.ndarray) -> Dict[str, Any]:
        """Run detection on frame"""
        result = {
            'faces': [],
            'face_count': 0,
            'phones': [],
            'books': [],
            'persons': [],
            'person_count': 0
        }
        
        if self.model:
            try:
                predictions = self.model.predict(frame, verbose=False, conf=0.35)
                
                for pred in predictions:
                    for box in pred.boxes:
                        cls_id = int(box.cls[0])
                        conf = float(box.conf[0])
                        bbox = box.xyxy[0].cpu().numpy().tolist()
                        
                        detection = {
                            'bbox': bbox,
                            'confidence': round(conf, 2)
                        }
                        
                        if cls_id == self.CLASS_PERSON:
                            result['persons'].append(detection)
                            result['person_count'] += 1
                        elif cls_id == self.CLASS_PHONE:
                            result['phones'].append(detection)
                        elif cls_id == self.CLASS_BOOK:
                            result['books'].append(detection)
                
            except Exception as e:
                logger.error(f"YOLO detection error: {e}")
        
        # Fallback face detection with OpenCV
        if self.face_cascade is not None and result['person_count'] == 0:
            try:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
                for (x, y, w, h) in faces:
                    result['faces'].append({
                        'bbox': [x, y, x+w, y+h],
                        'confidence': 0.8
                    })
                result['face_count'] = len(result['faces'])
            except:
                pass
        else:
            # Use person detections as face count approximation
            result['face_count'] = result['person_count']
            result['faces'] = result['persons']
        
        return result


# ==========================================
# 2. GAZE ESTIMATOR (OpenCV-based, no MediaPipe)
# ==========================================
class GazeEstimator:
    """
    Simple gaze estimation using OpenCV eye detection
    No MediaPipe dependency
    """
    
    def __init__(self):
        self.eye_cascade = None
        self.face_cascade = None
        
        if cv2_available:
            try:
                self.face_cascade = cv2.CascadeClassifier(
                    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                )
                self.eye_cascade = cv2.CascadeClassifier(
                    cv2.data.haarcascades + 'haarcascade_eye.xml'
                )
            except:
                pass
    
    def estimate(self, frame: np.ndarray) -> Dict[str, Any]:
        """Estimate gaze direction"""
        if not self.face_cascade or not self.eye_cascade:
            return {'gaze_score': 0, 'looking_away': False, 'eyes_detected': False}
        
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
            
            if len(faces) == 0:
                return {'gaze_score': 50, 'looking_away': True, 'no_face': True}
            
            # Take first face
            (x, y, w, h) = faces[0]
            roi_gray = gray[y:y+h, x:x+w]
            
            # Detect eyes in face region
            eyes = self.eye_cascade.detectMultiScale(roi_gray)
            
            if len(eyes) < 2:
                # Less than 2 eyes visible = possibly looking away
                return {
                    'gaze_score': 40,
                    'looking_away': True,
                    'eyes_detected': len(eyes),
                    'reason': 'eyes_not_visible'
                }
            
            # Both eyes visible, calculate gaze
            # Get eye positions relative to face center
            face_center_x = w / 2
            eye_positions = []
            
            for (ex, ey, ew, eh) in eyes[:2]:
                eye_center_x = ex + ew / 2
                eye_positions.append(eye_center_x)
            
            # Calculate asymmetry (indicates looking left/right)
            avg_eye_pos = sum(eye_positions) / 2
            deviation = abs(avg_eye_pos - face_center_x) / face_center_x
            
            gaze_score = min(100, deviation * 100)
            looking_away = deviation > 0.3
            
            return {
                'gaze_score': round(gaze_score, 1),
                'looking_away': looking_away,
                'eyes_detected': len(eyes),
                'deviation': round(deviation, 2)
            }
            
        except Exception as e:
            logger.error(f"Gaze estimation error: {e}")
            return {'gaze_score': 0, 'looking_away': False}


# ==========================================
# 3. SCREENSHOT DETECTOR
# ==========================================
class ScreenshotDetector:
    """
    Detect screenshot attempts via:
    - PrintScreen key monitoring
    - Known screenshot tool processes
    - Screen recording software
    """
    
    SCREENSHOT_PROCESSES = [
        'snippingtool', 'snip', 'lightshot', 'greenshot', 
        'sharex', 'screenpresso', 'obs64', 'obs32', 
        'camtasia', 'bandicam', 'xboxgamebar'
    ]
    
    def __init__(self):
        self.last_check = time.time()
        self.screenshot_count = 0
    
    def check(self) -> Dict[str, Any]:
        """Check for screenshot activity"""
        result = {
            'screenshot_detected': False,
            'recording_detected': False,
            'suspicious_processes': []
        }
        
        if not psutil_available:
            return result
        
        try:
            for proc in psutil.process_iter(['name']):
                name = proc.info['name'].lower()
                for ss_proc in self.SCREENSHOT_PROCESSES:
                    if ss_proc in name:
                        result['suspicious_processes'].append(name)
                        if 'obs' in name or 'camtasia' in name or 'bandicam' in name:
                            result['recording_detected'] = True
                        else:
                            result['screenshot_detected'] = True
        except:
            pass
        
        return result
    
    def detect_printscreen(self) -> bool:
        """
        Note: This requires keyboard hook which needs admin rights
        For browser-based, use JavaScript API instead
        """
        return False


# ==========================================
# 4. TAB CHANGE DETECTOR
# ==========================================
class TabChangeDetector:
    """Track tab/window focus changes"""
    
    def __init__(self):
        self.tab_switches = []
        self.last_focus_time = time.time()
        self.total_switches = 0
    
    def record_switch(self, session_id: str, details: str = None) -> Dict[str, Any]:
        """Record a tab switch event"""
        now = time.time()
        time_since_last = now - self.last_focus_time
        
        self.tab_switches.append({
            'timestamp': now,
            'time_away': time_since_last,
            'details': details
        })
        self.total_switches += 1
        self.last_focus_time = now
        
        # Keep only last 20 switches
        self.tab_switches = self.tab_switches[-20:]
        
        # Calculate suspicion based on frequency
        recent_switches = [s for s in self.tab_switches if now - s['timestamp'] < 60]
        switches_per_minute = len(recent_switches)
        
        return {
            'suspicious': switches_per_minute > 3,
            'alert_type': 'TAB_SWITCH',
            'score': min(100, switches_per_minute * 25),
            'total_switches': self.total_switches,
            'switches_per_minute': switches_per_minute
        }
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            'total_switches': self.total_switches,
            'recent_switches': len(self.tab_switches)
        }


# ==========================================
# 5. COPY/PASTE DETECTOR
# ==========================================
class CopyPasteDetector:
    """Detect copy/paste of question content"""
    
    def __init__(self):
        self.copy_events = []
        self.paste_events = []
        self.question_hashes = set()
    
    def register_question(self, question_text: str):
        """Register a question to detect if it's copied"""
        # Store hash of question (normalized)
        normalized = question_text.lower().strip()
        self.question_hashes.add(hash(normalized))
    
    def check_copy(self, copied_text: str, session_id: str) -> Dict[str, Any]:
        """Check if copied content matches question"""
        normalized = copied_text.lower().strip()
        content_hash = hash(normalized)
        
        is_question_copy = content_hash in self.question_hashes
        
        event = {
            'timestamp': time.time(),
            'content_length': len(copied_text),
            'is_question': is_question_copy
        }
        self.copy_events.append(event)
        
        # High suspicion if copying question text
        if is_question_copy:
            return {
                'suspicious': True,
                'alert_type': 'QUESTION_COPIED',
                'score': 95,
                'details': 'Student copied exam question text'
            }
        elif len(copied_text) > 50:
            return {
                'suspicious': True,
                'alert_type': 'LARGE_COPY',
                'score': 60,
                'details': f'Copied {len(copied_text)} characters'
            }
        
        return {'suspicious': False, 'alert_type': 'COPY', 'score': 20}
    
    def check_paste(self, pasted_text: str, session_id: str) -> Dict[str, Any]:
        """Check paste event"""
        event = {
            'timestamp': time.time(),
            'content_length': len(pasted_text)
        }
        self.paste_events.append(event)
        
        # Suspicious if pasting large content
        if len(pasted_text) > 100:
            return {
                'suspicious': True,
                'alert_type': 'LARGE_PASTE',
                'score': 70,
                'details': f'Pasted {len(pasted_text)} characters'
            }
        
        return {'suspicious': False, 'alert_type': 'PASTE', 'score': 15}


# ==========================================
# 6. TEMPORAL SMOOTHER
# ==========================================
class TemporalSmoother:
    """Smooth scores over time"""
    
    def __init__(self, window: int = 5, alpha: float = 0.3):
        self.window = window
        self.alpha = alpha
        self.histories: Dict[str, Dict[str, deque]] = {}
    
    def smooth(self, session_id: str, signal: str, value: float) -> float:
        if session_id not in self.histories:
            self.histories[session_id] = {}
        if signal not in self.histories[session_id]:
            self.histories[session_id][signal] = deque(maxlen=self.window)
        
        history = self.histories[session_id][signal]
        history.append(value)
        
        if len(history) == 1:
            return value
        
        ema = history[0]
        for v in list(history)[1:]:
            ema = self.alpha * v + (1 - self.alpha) * ema
        return ema


# ==========================================
# 7. CERTAINTY ENGINE
# ==========================================
class CertaintyEngine:
    """Multi-signal confidence aggregation"""
    
    def calculate(self, signals: Dict[str, float]) -> Dict[str, Any]:
        if not signals:
            return {'score': 0, 'confidence': 0, 'verdict': 'SAFE'}
        
        active = {k: v for k, v in signals.items() if v > 10}
        
        if not active:
            return {'score': 0, 'confidence': 0, 'verdict': 'SAFE'}
        
        # Weighted average with boost for multiple signals
        max_score = max(active.values())
        avg_score = sum(active.values()) / len(active)
        
        # Multi-signal boost
        boost = 1 + (len(active) - 1) * 0.1
        final_score = min(100, (max_score * 0.6 + avg_score * 0.4) * boost)
        
        confidence = min(1.0, len(active) * 0.2 + final_score / 200)
        
        verdict = 'SAFE'
        if final_score >= 75: verdict = 'CRITICAL'
        elif final_score >= 50: verdict = 'HIGH'
        elif final_score >= 30: verdict = 'MILD'
        
        return {
            'score': round(final_score, 1),
            'confidence': round(confidence, 2),
            'verdict': verdict,
            'active_signals': len(active)
        }


# ==========================================
# 8. AUDIO ANALYZER (NumPy only)
# ==========================================
class AudioAnalyzer:
    """Audio analysis without external dependencies"""
    
    def analyze(self, audio: np.ndarray, sr: int = 44100) -> Dict[str, Any]:
        if len(audio) == 0:
            return {'suspicious': False}
        
        try:
            audio = audio.astype(np.float32)
            if audio.max() > 1.0:
                audio = audio / 32768.0
            
            # RMS volume
            rms = np.sqrt(np.mean(audio**2))
            db = 20 * np.log10(rms + 1e-10)
            
            # FFT for keyboard detection
            fft = np.fft.fft(audio)
            freqs = np.fft.fftfreq(len(audio), 1/sr)
            
            # Keyboard clicks: 2-8kHz
            kb_mask = (np.abs(freqs) > 2000) & (np.abs(freqs) < 8000)
            kb_energy = np.sum(np.abs(fft[kb_mask]))
            total = np.sum(np.abs(fft)) + 1e-10
            kb_ratio = kb_energy / total
            
            keyboard = kb_ratio > 0.25
            loud = db > -20
            
            score = 0
            if keyboard: score += 70
            if loud: score += 20
            
            return {
                'suspicious': score > 30,
                'score': score,
                'keyboard_detected': keyboard,
                'high_volume': loud,
                'volume_db': round(db, 1)
            }
        except:
            return {'suspicious': False}


# ==========================================
# 9. SYSTEM MONITOR
# ==========================================
class SystemMonitor:
    """Monitor suspicious processes"""
    
    SUSPICIOUS = [
        'obs', 'teamviewer', 'anydesk', 'discord', 'zoom', 
        'skype', 'telegram', 'whatsapp', 'chrome', 'firefox',
        'edge', 'brave'  # Browser detection for multiple windows
    ]
    
    def check(self) -> Dict[str, Any]:
        if not psutil_available:
            return {'detected': False}
        
        try:
            found = []
            browsers = 0
            
            for proc in psutil.process_iter(['name']):
                name = proc.info['name'].lower()
                for susp in self.SUSPICIOUS:
                    if susp in name:
                        if susp in ['chrome', 'firefox', 'edge', 'brave']:
                            browsers += 1
                        else:
                            found.append(name)
                        break
            
            # Multiple browser instances = suspicious
            multi_browser = browsers > 2
            
            return {
                'detected': len(found) > 0 or multi_browser,
                'processes': found,
                'browser_count': browsers,
                'multi_browser_alert': multi_browser
            }
        except:
            return {'detected': False}


# ==========================================
# MAIN CHEATDETECTOR CLASS
# ==========================================
class CheatDetector:
    """
    Unified CheatDetector - No MediaPipe
    =====================================
    Features:
    ✅ YOLO Face Detection (multiple faces)
    ✅ YOLO Phone/Book Detection
    ✅ OpenCV Gaze Estimation
    ✅ Screenshot Detection
    ✅ Tab Change Detection
    ✅ Copy/Paste Detection
    ✅ Audio Analysis
    ✅ Temporal Smoothing
    ✅ Certainty Engine
    ✅ Mesa ABM Integration
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.log_file = self.config.get('log_file', 'suspicion_log.json')
        
        # Lazy initialization variables
        self._yolo = None
        self._gaze = None
        self._mesa = None
        
        # Initialize lightweight detectors eagerly
        self.screenshot = ScreenshotDetector()
        self.tab_detector = TabChangeDetector()
        self.copy_detector = CopyPasteDetector()
        self.audio = AudioAnalyzer()
        self.system = SystemMonitor()
        
        # Advanced Engines
        try:
            self.head_pose = HeadPoseEngine()
            self.hand_gesture = HandGestureEngine()
            self.keyboard_sound = KeyboardSoundDetector()
            self.behavioral = BehavioralAnalyzer()
            logger.info("Advanced engines initialized")
        except NameError:
            self.head_pose = None
            self.hand_gesture = None
            self.keyboard_sound = None
            self.behavioral = None
            logger.info("Advanced engines not available")
        
        # Temporal & Certainty (Lightweight)
        self.smoother = TemporalSmoother()
        self.certainty = CertaintyEngine()
        
        logger.info("CheatDetector initialized (MediaPipe-free)")

    @property
    def yolo(self):
        """Lazy load YOLO Detector"""
        if self._yolo is None:
            logger.info("Lazy loading YOLO Detector...")
            self._yolo = YOLODetector()
        return self._yolo

    @property
    def gaze(self):
        """Lazy load Gaze Estimator"""
        if self._gaze is None:
            logger.info("Lazy loading Gaze Estimator...")
            self._gaze = GazeEstimator()
        return self._gaze

    @property
    def mesa(self):
        """Lazy load Mesa Service"""
        if self._mesa is None:
            try:
                logger.info("Lazy loading Mesa Service...")
                from backend.services.mesa_service import MesaService
                self._mesa = MesaService()
            except ImportError:
                # logger.warning("Mesa Service not available")
                self._mesa = None
            except Exception as e:
                logger.warning(f"Failed to load Mesa: {e}")
                self._mesa = None
        return self._mesa
    
    def analyze_frame(self, frame_data: str, session_id: str = None) -> Dict[str, Any]:
        """Main frame analysis"""
        if not cv2_available:
            return {'suspicious': False, 'error': 'OpenCV missing'}
        
        try:
            # Decode
            if ',' in frame_data:
                frame_data = frame_data.split(',')[-1]
            frame = cv2.imdecode(
                np.frombuffer(base64.b64decode(frame_data), np.uint8),
                cv2.IMREAD_COLOR
            )
            if frame is None:
                return {'suspicious': False, 'error': 'Invalid frame'}
            
            signals = {}
            details = {}
            
            # 1. YOLO Detection (faces, phones, books)
            yolo_result = self.yolo.detect(frame)
            details['yolo'] = yolo_result
            
            # Multiple faces
            if yolo_result['face_count'] > 1:
                signals['multiple_faces'] = 90
            elif yolo_result['face_count'] == 0:
                signals['no_face'] = 80
            
            # Phone detected
            if yolo_result['phones']:
                signals['phone'] = 95
            
            # Book detected
            if yolo_result['books']:
                signals['book'] = 70
            
            # 2. Gaze Estimation
            gaze_result = self.gaze.estimate(frame)
            details['gaze'] = gaze_result
            if gaze_result.get('looking_away'):
                signals['gaze'] = gaze_result.get('gaze_score', 40)
                
            # Advanced Head Pose
            if getattr(self, 'head_pose', None):
                head_result = self.head_pose.estimate_head_pose(frame)
                details['head_pose'] = head_result
                if head_result.get('suspicious'):
                    signals['head_pose'] = 80
                    
            # Advanced Hand Gestures
            if getattr(self, 'hand_gesture', None):
                hand_result = self.hand_gesture.detect_gestures(frame)
                details['hand_gesture'] = hand_result
                if hand_result.get('phone_call'): signals['phone_call'] = 95
                if hand_result.get('camera_block'): signals['camera_block'] = 90
            
            # 3. Screenshot check
            ss_result = self.screenshot.check()
            details['screenshot'] = ss_result
            if ss_result.get('screenshot_detected'):
                signals['screenshot'] = 85
            if ss_result.get('recording_detected'):
                signals['recording'] = 95
            
            # Apply smoothing
            if session_id:
                for k in signals:
                    signals[k] = self.smoother.smooth(session_id, k, signals[k])
            
            # Certainty calculation
            cert = self.certainty.calculate(signals)
            
            # Determine primary alert
            alert_type = 'NONE'
            if signals:
                alert_type = max(signals, key=signals.get).upper()
            
            result = {
                'suspicious': cert['verdict'] in ['HIGH', 'CRITICAL'],
                'suspicion_score': cert['score'],
                'confidence': cert['confidence'],
                'verdict': cert['verdict'],
                'alert_type': alert_type,
                'details': details,
                'signals': signals,
                # Key detections for UI
                'face_count': yolo_result['face_count'],
                'phone_detected': len(yolo_result['phones']) > 0,
                'book_detected': len(yolo_result['books']) > 0,
                'looking_away': gaze_result.get('looking_away', False)
            }
            
            # Mesa event
            if session_id and self.mesa:
                try:
                    self.mesa.process_event(session_id, {
                        'type': 'FRAME', 'score': cert['score'],
                        'signals': signals, 'timestamp': time.time()
                    })
                except:
                    pass
            
            if result['suspicious'] and session_id:
                self.log_alert(session_id, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Frame analysis error: {e}")
            return {'suspicious': False, 'error': str(e)}
    
    def analyze_audio(self, audio_data, session_id: str = None, sr: int = 44100) -> Dict[str, Any]:
        """Audio analysis"""
        try:
            if isinstance(audio_data, str):
                audio_data = base64.b64decode(audio_data.split(',')[-1])
            if isinstance(audio_data, bytes):
                audio = np.frombuffer(audio_data, dtype=np.float32)
            else:
                audio = np.array(audio_data, dtype=np.float32)
            
            result = self.audio.analyze(audio, sr)
            
            # Advanced Keyboard Sound detection
            if getattr(self, 'keyboard_sound', None):
                kb_result = self.keyboard_sound.detect_keyboard_typing(audio, sr)
                result['advanced_keyboard'] = kb_result
                if kb_result.get('detected'):
                    result['suspicious'] = True
                    result['score'] = max(result.get('score', 0), 80)
            
            return result
        except:
            return {'suspicious': False}
    
    def handle_tab_switch(self, session_id: str, details: str = None) -> Dict[str, Any]:
        """Record tab switch"""
        result = self.tab_detector.record_switch(session_id, details)
        if self.mesa:
            try:
                self.mesa.process_event(session_id, {'type': 'TAB_SWITCH', 'timestamp': time.time()})
            except:
                pass
        return result
    
    def handle_copy(self, session_id: str, content: str) -> Dict[str, Any]:
        """Handle copy event"""
        result = self.copy_detector.check_copy(content, session_id)
        if self.mesa and result['suspicious']:
            try:
                self.mesa.process_event(session_id, {'type': 'COPY', 'timestamp': time.time()})
            except:
                pass
        return result
    
    def handle_paste(self, session_id: str, content: str) -> Dict[str, Any]:
        """Handle paste event"""
        result = self.copy_detector.check_paste(content, session_id)
        if self.mesa and result['suspicious']:
            try:
                self.mesa.process_event(session_id, {'type': 'PASTE', 'timestamp': time.time()})
            except:
                pass
        return result
    
    def register_question(self, question_text: str):
        """Register question for copy detection"""
        self.copy_detector.register_question(question_text)
    
    def check_system(self, session_id: str = None) -> Dict[str, Any]:
        """System monitoring"""
        return self.system.check()
    
    def check_screenshot(self, session_id: str = None) -> Dict[str, Any]:
        """Screenshot detection"""
        return self.screenshot.check()
    
    def get_tab_stats(self, session_id: str) -> Dict[str, Any]:
        """Get tab switching statistics"""
        return self.tab_detector.get_stats()
    
    def log_alert(self, session_id: str, result: Dict):
        try:
            entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'session_id': session_id,
                'alert_type': result.get('alert_type'),
                'score': result.get('suspicion_score'),
                'confidence': result.get('confidence'),
                'verdict': result.get('verdict')
            }
            
            logs = []
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r') as f:
                    logs = json.load(f)
            
            logs.append(entry)
            
            with open(self.log_file, 'w') as f:
                json.dump(logs[-100:], f, indent=2)
        except:
            pass
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

# YOLOv8 Object Detection
try:
    from ultralytics import YOLO
    ultralytics_available = True
except ImportError:
    ultralytics_available = False
    logger.warning("Ultralytics not available for object detection")


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


# ==========================================
# 6. Object Detector (YOLOv8)
# ==========================================
class ObjectDetector:
    """Detects objects like phones, books using YOLOv8"""
    
    def __init__(self):
        self.model = None
        if ultralytics_available:
            try:
                # Load a pretrained YOLOv8n model
                # It will download automatically on first run if not present
                self.model = YOLO("yolov8n.pt")
                # Suppress logging
                logging.getLogger("ultralytics").setLevel(logging.WARNING)
                logger.info("ObjectDetector (YOLOv8) initialized")
            except Exception as e:
                logger.error(f"Failed to load YOLOv8 model: {e}")

    def detect_objects(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Detect objects in frame
        Returns: {'found': ['cell phone', 'book'], 'scores': {...}}
        """
        if not self.model:
            return {'found': [], 'scores': {}, 'count': 0}
            
        try:
            # Predict
            results = self.model.predict(frame, verbose=False, conf=0.4)
            
            found_objects = []
            scores = {}
            
            # Map of class IDs to names (YOLOv8 COCO)
            # 67: cell phone, 73: book, 0: person, 63: laptop
            target_classes = {
                67: 'cell phone',
                73: 'book',
                # 63: 'laptop', # Laptop might be normal
                # 0: 'person' # Handled by face detection usually
            }
            
            for r in results:
                for box in r.boxes:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    
                    if cls_id in target_classes:
                        obj_name = target_classes[cls_id]
                        if obj_name not in found_objects:
                            found_objects.append(obj_name)
                            scores[obj_name] = conf
            
            return {
                'found': found_objects,
                'scores': scores,
                'count': len(found_objects)
            }
            
        except Exception as e:
            logger.error(f"Object detection error: {e}")
            return {'found': [], 'scores': {}, 'count': 0}

