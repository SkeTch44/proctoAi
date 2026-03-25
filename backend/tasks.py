import os
import logging
from datetime import datetime
from flask_socketio import SocketIO
from backend.celery_app import celery
# from backend.models.cheat_detector import CheatDetector (moved to accessor)

# Configure logger
logger = logging.getLogger(__name__)

# from backend.db.database import DatabaseManager (moved to accessor)

# Initialize dependencies
redis_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
db_url = os.getenv('DATABASE_URL', 'sqlite:///exam_platform.db')

socketio = SocketIO(message_queue=redis_url)

# Lazy loading components
_cheat_detector = None
_db_manager = None


def get_cheat_detector():
    global _cheat_detector
    if _cheat_detector is None:
        logger.info("Lazy loading CheatDetector in worker...")
        from backend.models.cheat_detector import CheatDetector
        _cheat_detector = CheatDetector()
    return _cheat_detector

def get_db_manager():
    global _db_manager
    if _db_manager is None:
        logger.info("Lazy loading DatabaseManager in worker...")
        from backend.db.database import DatabaseManager
        _db_manager = DatabaseManager(db_url)
    return _db_manager

@celery.task
def analyze_frame_task(session_id, frame_data, audio_data=None):
    """
    Background task to analyze frames using DeepFace.
    Emits results back to Flask-SocketIO via Redis.
    Logs suspicious events to Database.
    """
    try:
        # Default analysis results
        analysis_result = {}
        
        # Analyze frame if present
        if frame_data:
            analysis_result = get_cheat_detector().analyze_frame(frame_data, session_id=session_id)
        
        # Analyze audio if present
        if audio_data:
            audio_result = get_cheat_detector().analyze_audio(audio_data, session_id=session_id)
            
            # Merge results (prioritize high severity)
            if audio_result.get('suspicious'):
                if not analysis_result.get('suspicious') or \
                   audio_result.get('suspicion_score', 0) > analysis_result.get('suspicion_score', 0):
                    analysis_result = audio_result
        
        # Action if suspicious
        if analysis_result.get('suspicious'):
            # 1. Emit Real-time Alert
            socketio.emit('proctoring_alert', {
                'session_id': session_id,
                'alert_type': analysis_result.get('alert_type'),
                'confidence': analysis_result.get('confidence'),
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'details': analysis_result.get('details')
            }, room='admins')
            
            # 2. Persist to Database
            try:
                # Severity mapping
                score = analysis_result.get('suspicion_score', 0)
                severity = 'low'
                if score > 70: severity = 'high'
                elif score > 30: severity = 'medium'
                
                get_db_manager().log_proctoring_event(
                    session_id=session_id,
                    event_type=analysis_result.get('alert_type'),
                    severity=severity,
                    details=str(analysis_result.get('details'))
                )
                get_db_manager().update_suspicion_score(session_id, int(score / 5)) # Simple scaling
            except Exception as db_e:
                logger.error(f"Failed to log to DB: {db_e}")
            
    except Exception as e:
        logger.error(f"Error in analyze_frame_task: {e}")


