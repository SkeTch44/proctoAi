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

try:
    from ultralytics import YOLO
    ultralytics_available = True
except ImportError:
    ultralytics_available = False
    logger.warning("YOLOv8 not available")

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
try:
    from backend.mesa_engine.behavior_model import MesaService
    mesa_available = True
except ImportError:
    mesa_available = False


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
        
        if ultralytics_available:
            try:
                self.model = YOLO("yolov8n.pt")
                logging.getLogger("ultralytics").setLevel(logging.WARNING)
                logger.info("YOLO model loaded successfully")
            except Exception as e:
                logger.error(f"YOLO init failed: {e}")
        
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
        
        # Initialize detectors
        self.yolo = YOLODetector()
        self.gaze = GazeEstimator()
        self.screenshot = ScreenshotDetector()
        self.tab_detector = TabChangeDetector()
        self.copy_detector = CopyPasteDetector()
        self.audio = AudioAnalyzer()
        self.system = SystemMonitor()
        
        # Temporal & Certainty
        self.smoother = TemporalSmoother()
        self.certainty = CertaintyEngine()
        
        # Mesa
        self.mesa = None
        if mesa_available:
            try:
                self.mesa = MesaService()
            except:
                pass
        
        logger.info("CheatDetector initialized (MediaPipe-free)")
    
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
            
            return self.audio.analyze(audio, sr)
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
