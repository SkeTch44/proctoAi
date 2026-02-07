<<<<<<< HEAD
# import cv2
# import numpy as np
# import base64
# import json
# import logging 
# from typing import List, Tuple, Dict, Any
# from datetime import datetime, timedelta

# from PIL import Image
# import mediapipe as mp 
# import threading
# import time
# import math

# #  optional imorts with fallbacks 
# try:
#     from deepface import DeepFace
#     deepface_available = True
# except ImportError:
#     deepface_available = False
#     logging.warning("DeepFace is not available. Some features may be disabled.")

# try:
#     import dlib
#     dlib_available = True
# except ImportError:
#     dlib_available = False
#     logging.warning("dlib is not available. Some features may be disabled.")

# logger = logging.getLogger(__name__)

# class CheatDetector:
    
#     """Advanced AI-Powered Cheat Detection System for proctored Exam
#     Features:
#     - Real-time face detection and tracking
#     - Multiple person detection and tracking
#     - Gaze tracking and attention monitoring
#     - Suspicious behaviour analysis
#     - mobile device detection
#     - Screen sharing detection
#     - Gesture recognition
#     - Emotion analysis using DeepFace
#      """

# def SuspiciousPatternDetector():
#     raise NotImplementedError

# def BehaviorTracker():
#     raise NotImplementedError

# def __init__(self,config : dict  = None):
#         self.config = config or self._get_default_config()
#         self.reference_face = None 
#         self.baseline_behaviour = {}
#         self.suspicious_activites = []
#         self.frame_history =[]
#         self.audio_history = []
#         self.session_start_time = None 
#         self.last_analysis_time = time.time ()

#         #  intialize Mediapipe componets 
#         self._init_mediapipe()
#             #  intialize face recognition
#         self._init_face_recognition()
#         # Behaviour tracking and suspicious pattern detector
#         self.behaviour_tracker = BehaviorTracker()
#         self.pattern_detector = SuspiciousPatternDetector()
        
#         logger.info("chetaer detector Initialized Sucessfully")

#         def _get_default_config(self) -> Dict:
#             """Get default confiuguration for cheat Detection
#             """
#         return{
#             'Face_confidence_threshold': 0.8,
#             'emotion_threshold ': 0.7,
#             'gaze_thershold ': 0.15,
#             'multiple_face_threshold ': 2,
#             'suspicious_movement_threshold':0.4,
#             'audio_anomaly_threshold ': 0.6,
#             'frame_analysis_interval':1.0, # seconds
#             'max_frame_history': 100,
#             'enable_face_recoginition ': True,
#             'enable_emotion_analysis': True,
#             'enable_gaze_tracking': True,
#             'enable_gesture_recognition': True,
#             'enable_audio_analysis': True,
#             'alert_cooldown_secounds': 5,
#             'behavior_learning_frames':50

#         }

def _init_mediapipe(self):
        """Initialize Mediapipe components"""
try:
            # face detection 
        self.mp_face_detection  = mp.solutions.face_detection
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_drawing = mp.solutions.drawing_utils
except Exception as e:
        logger.error(f"Error initializing Mediapipe components: {e}")
=======
import base64
import json
import logging 
from typing import Dict, Any, Optional
from datetime import datetime
import os

try:
    import cv2
    cv2_available = True
except ImportError:
    cv2_available = False
    logging.warning("OpenCV is not available. Frame analysis disabled.")

try:
    import numpy as np
    numpy_available = True
except ImportError:
    numpy_available = False
    logging.warning("NumPy is not available. Frame analysis disabled.")


try:
    import mediapipe as mp
    mediapipe_available = True
except ImportError:
    mediapipe_available = False
    logging.warning("MediaPipe is not available. Some features may be disabled.")

try:
    from deepface import DeepFace
    deepface_available = True
except ImportError:
    deepface_available = False
    logging.warning("DeepFace is not available. Some features may be disabled.")

logger = logging.getLogger(__name__)


class CheatDetector:
    """
    Advanced AI-Powered Cheat Detection System for Proctored Exams
    
    Features:
    - Real-time face detection and tracking
    - Multiple person detection
    - Gaze tracking and attention monitoring
    - Emotion analysis using DeepFace
    - Weighted suspicion scoring
    - JSON-based alert logging
    """
    
    SCALE = 1
    
    WEIGHTS = {
        'gaze': 0.15,           # 15%
        'face_absence': 0.35,   # 35% - High Priority
        'multiple_faces': 0.30, # 30% - High Priority
        'emotion': 0.05,        # 5%
        'mic': 0.05,            # 5%
        'tab_switch': 0.10      # 10%
    }
    
    # Audio constants
    AUDIO_THRESHOLD_DB = 60.0  # Decibels
    
    # Threshold definitions
    THRESHOLDS = {
        'LOW': (1, 30),
        'MEDIUM': (31, 70),
        'HIGH': (71, 100)
    }
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize CheatDetector with optional configuration"""
        self.config = config or self._get_default_config()
        self.log_file = self.config.get('log_file', 'suspicion_log.json')
        
        # Initialize MediaPipe if available
        if mediapipe_available:
            self._init_mediapipe()
        else:
            logger.warning("MediaPipe not available. Face detection disabled.")
            self.mp_face_detection = None
            self.mp_face_mesh = None
        
        logger.info("CheatDetector initialized successfully")
    
    def _get_default_config(self) -> Dict:
        """Get default configuration for cheat detection"""
        return {
            'face_confidence_threshold': 0.8,
            'emotion_threshold': 0.7,
            'gaze_threshold': 0.15,
            'multiple_face_threshold': 2,
            'log_file': 'suspicion_log.json',
            'enable_face_detection': True,
            'enable_emotion_analysis': True,
            'enable_gaze_tracking': True
        }
    
    def _init_mediapipe(self):
        """Initialize MediaPipe components"""
        try:
            # Fix for Windows AttributeError: module 'mediapipe' has no attribute 'solutions'
            if not hasattr(mp, 'solutions'):
                try:
                    import mediapipe.python.solutions as solutions
                    mp.solutions = solutions
                except ImportError:
                    pass

            self.mp_face_detection = mp.solutions.face_detection
            self.mp_face_mesh = mp.solutions.face_mesh
            self.mp_drawing = mp.solutions.drawing_utils
            logger.info("MediaPipe initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing MediaPipe components: {e}")
            self.mp_face_detection = None
            self.mp_face_mesh = None
    
    
    def analyze_audio(self, audio_data: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze audio chunk for high volume (indicating potential communication)
        """
        if not numpy_available:
            return {'suspicious': False, 'score': 0}

        try:
            # Decode audio (assuming base64 encoded PCM or similar raw chunks)
            # For simplicity in this demo, we'll estimate volume from byte amplitude
            audio_bytes = base64.b64decode(audio_data)
            audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
            
            if len(audio_array) == 0:
                return {'suspicious': False, 'score': 0}
            
            # Calculate RMS amplitude
            rms = np.sqrt(np.mean(audio_array.astype(np.float32)**2))
            
            # Convert to decibels (relative to max int16 value 32768)
            # Avoid log(0)
            if rms > 0:
                db = 20 * np.log10(rms)
            else:
                db = -np.inf
                
            # Check threshold (adjust normalizer based on real mic input range)
            # Assuming db value around 40-90 range usually
            suspicious = db > self.AUDIO_THRESHOLD_DB
            
            result = {
                'suspicious': suspicious,
                'suspicion_score': 100 if suspicious else 0,
                'severity': 'MEDIUM' if suspicious else 'LOW',
                'alert_type': 'HIGH_VOLUME_DETECTED',
                'confidence': 0.8,
                'details': {
                    'decibels': round(float(db), 2),
                    'rms_amplitude': round(float(rms), 2)
                }
            }
            
            if suspicious and session_id:
                self.log_alert(session_id, result)
                
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing audio: {e}")
            return {'suspicious': False, 'error': str(e)}

    def analyze_frame(self, frame_data: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Main entry point for analyzing a frame
        
        Args:
            frame_data: Base64-encoded image data
            session_id: Optional session identifier
        
        Returns:
            Dictionary containing analysis results and suspicion score
        """
        if not cv2_available or not numpy_available:
            logger.warning("Cannot analyze frame: cv2 or numpy not available")
            return {
                'suspicious': False,
                'suspicion_score': 0,
                'severity': 'LOW',
                'error': 'cv2 or numpy not available'
            }
        
        try:
            # Decode base64 frame
            img_bytes = base64.b64decode(frame_data.split(',')[-1])
            nparr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Analyze different aspects
            gaze_score = self._analyze_gaze(frame)
            face_absence_score = self._analyze_face_presence(frame)
            multiple_faces_score = self._analyze_multiple_faces(frame)
            emotion_score = self._analyze_emotion(frame)
            
            # Calculate total suspicion score
            total_score = self.calculate_suspicion_score(
                gaze_score=gaze_score,
                face_absence_score=face_absence_score,
                multiple_faces_score=multiple_faces_score,
                emotion_score=emotion_score,
                mic_score=0,  # Placeholder for audio analysis
                tab_switch_score=0  # Placeholder for tab switch detection
            )
            
            # Classify severity
            severity = self._classify_severity(total_score)
            
            # Determine if suspicious
            suspicious = severity in ['MEDIUM', 'HIGH']
            
            # Prepare result
            result = {
                'suspicious': suspicious,
                'suspicion_score': round(total_score, 2),
                'severity': severity,
                'alert_type': self._determine_alert_type(
                    gaze_score, face_absence_score, multiple_faces_score, emotion_score
                ),
                'confidence': round(total_score / 100, 2),
                'details': {
                    'gaze_deviation': round(gaze_score, 2),
                    'face_absence': round(face_absence_score, 2),
                    'multiple_faces': round(multiple_faces_score, 2),
                    'emotion_anomaly': round(emotion_score, 2)
                }
            }
            
            # Log alert if suspicious
            if suspicious and session_id:
                self.log_alert(session_id, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing frame: {e}")
            return {
                'suspicious': False,
                'suspicion_score': 0,
                'severity': 'LOW',
                'error': str(e)
            }
    
    def calculate_suspicion_score(
        self,
        gaze_score: float,
        face_absence_score: float,
        multiple_faces_score: float,
        emotion_score: float,
        mic_score: float,
        tab_switch_score: float
    ) -> float:
        """
        Calculate weighted suspicion score
        
        Args:
            Individual anomaly scores (0-100 scale)
        
        Returns:
            Total suspicion score (0-100)
        """
        score = (
            (gaze_score * self.WEIGHTS['gaze']) +
            (face_absence_score * self.WEIGHTS['face_absence']) +
            (multiple_faces_score * self.WEIGHTS['multiple_faces']) +
            (emotion_score * self.WEIGHTS['emotion']) +
            (mic_score * self.WEIGHTS['mic']) +
            (mic_score * self.WEIGHTS['mic']) +
            (tab_switch_score * self.WEIGHTS['tab_switch'])
        )
        
        # Ensure score is within bounds
        return max(0, min(100, score))

    def handle_tab_switch(self, session_id: str) -> Dict[str, Any]:
        """
        Handle a tab switch event. 
        Returns analysis result.
        """
        # Tab switching is always suspicious
        result = {
            'suspicious': True,
            'suspicion_score': 100 * self.WEIGHTS['tab_switch'] * 5, # High impact
            'severity': 'HIGH',
            'alert_type': 'TAB_SWITCH',
            'confidence': 1.0,
            'details': {
                'message': 'User switched tabs or lost focus'
            }
        }
        
        if session_id:
            self.log_alert(session_id, result)
            
        return result
    
    def _classify_severity(self, score: float) -> str:
        """Classify suspicion score into severity level"""
        if self.THRESHOLDS['LOW'][0] <= score <= self.THRESHOLDS['LOW'][1]:
            return 'LOW'
        elif self.THRESHOLDS['MEDIUM'][0] <= score <= self.THRESHOLDS['MEDIUM'][1]:
            return 'MEDIUM'
        elif self.THRESHOLDS['HIGH'][0] <= score <= self.THRESHOLDS['HIGH'][1]:
            return 'HIGH'
        return 'LOW'
    
    def _determine_alert_type(
        self, gaze: float, face_absence: float, multiple_faces: float, emotion: float
    ) -> str:
        """Determine primary alert type based on highest score"""
        scores = {
            'GAZE_DEVIATION': gaze,
            'FACE_ABSENCE': face_absence,
            'MULTIPLE_FACES': multiple_faces,
            'EMOTION_ANOMALY': emotion
        }
        return max(scores, key=scores.get) if max(scores.values()) > 0 else 'NONE'
    
    def _analyze_gaze(self, frame: np.ndarray) -> float:
        """Analyze gaze deviation (0-100 score)"""
        # Placeholder implementation
        # In production, use MediaPipe Face Mesh to track eye landmarks
        return 0.0
    
    def _analyze_face_presence(self, frame: np.ndarray) -> float:
        """Detect face absence (0-100 score)"""
        if not self.mp_face_detection:
            return 0.0
        
        try:
            with self.mp_face_detection.FaceDetection(min_detection_confidence=0.5) as face_detection:
                results = face_detection.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                
                # If no face detected, return high score
                if not results.detections:
                    return 100.0
                return 0.0
        except Exception as e:
            logger.error(f"Error in face presence analysis: {e}")
            return 0.0
    
    def _analyze_multiple_faces(self, frame: np.ndarray) -> float:
        """Detect multiple faces (0-100 score)"""
        if not self.mp_face_detection:
            return 0.0
        
        try:
            with self.mp_face_detection.FaceDetection(min_detection_confidence=0.5) as face_detection:
                results = face_detection.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                
                # If more than 1 face detected, return high score
                if results.detections and len(results.detections) > 1:
                    return 100.0
                return 0.0
        except Exception as e:
            logger.error(f"Error in multiple faces analysis: {e}")
            return 0.0
    
    def _analyze_emotion(self, frame: np.ndarray) -> float:
        """Analyze emotion anomalies using DeepFace (0-100 score)"""
        if not deepface_available:
            return 0.0
        
        try:
            # DeepFace emotion analysis
            analysis = DeepFace.analyze(frame, actions=['emotion'], enforce_detection=False)
            
            # Check for suspicious emotions (e.g., high fear, anger)
            emotions = analysis[0]['emotion'] if isinstance(analysis, list) else analysis['emotion']
            suspicious_score = emotions.get('fear', 0) + emotions.get('angry', 0)
            
            return min(100, suspicious_score)
        except Exception as e:
            logger.error(f"Error in emotion analysis: {e}")
            return 0.0
    
    def log_alert(self, session_id: str, result: Dict[str, Any]):
        """
        Append alert to suspicion_log.json
        
        Args:
            session_id: Session identifier
            result: Analysis result dictionary
        """
        try:
            alert_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'session_id': session_id,
                'alert_type': result.get('alert_type', 'UNKNOWN'),
                'severity': result.get('severity', 'LOW'),
                'score_impact': result.get('suspicion_score', 0),
                'details': result.get('details', {})
            }
            
            # Read existing log or create new
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r') as f:
                    logs = json.load(f)
            else:
                logs = []
            
            # Append new alert
            logs.append(alert_entry)
            
            # Write back to file
            with open(self.log_file, 'w') as f:
                json.dump(logs, f, indent=2)
            
            logger.info(f"Alert logged for session {session_id}: {result['alert_type']}")
            
        except Exception as e:
            logger.error(f"Error logging alert: {e}")
>>>>>>> rohan
