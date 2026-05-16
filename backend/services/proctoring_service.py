"""
Proctoring Service
Handles frame storage, audio analysis, and proctoring data persistence
"""

import os
import base64
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
import threading

logger = logging.getLogger(__name__)


class ProctoringService:
    """Service for managing proctoring-related operations"""
    
    def __init__(self, upload_base_path: str = 'backend/uploads'):
        self.upload_base_path = upload_base_path
        self.proctoring_dir = os.path.join(upload_base_path, 'proctoring')
        self.cleanup_age_days = 30
        
        # Ensure directories exist
        os.makedirs(self.proctoring_dir, exist_ok=True)
    
    def save_frame(self, session_id: int, frame_data: str, timestamp: str = None) -> bool:
        """
        Save a frame (JPEG base64) to disk
        
        Args:
            session_id: Exam session ID
            frame_data: Base64 encoded JPEG frame
            timestamp: ISO timestamp string (optional)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create session directory
            session_dir = os.path.join(self.proctoring_dir, str(session_id))
            os.makedirs(session_dir, exist_ok=True)
            
            # Generate filename
            if not timestamp:
                timestamp = datetime.utcnow().isoformat()
            
            # Remove special characters from timestamp for filename
            safe_timestamp = timestamp.replace(':', '-').replace('.', '_').split('Z')[0]
            filename = f"frame_{safe_timestamp}.jpg"
            filepath = os.path.join(session_dir, filename)
            
            # Decode and save
            if frame_data.startswith('data:image/jpeg;base64,'):
                frame_data = frame_data.replace('data:image/jpeg;base64,', '')
            
            frame_bytes = base64.b64decode(frame_data)
            
            with open(filepath, 'wb') as f:
                f.write(frame_bytes)
            
            logger.info(f"Frame saved: {filepath} ({len(frame_bytes)} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save frame: {e}")
            return False
    
    def get_session_frames(self, session_id: int) -> list:
        """
        Get list of saved frames for a session
        
        Args:
            session_id: Exam session ID
        
        Returns:
            List of frame file paths
        """
        try:
            session_dir = os.path.join(self.proctoring_dir, str(session_id))
            if not os.path.exists(session_dir):
                return []
            
            frames = []
            for filename in sorted(os.listdir(session_dir)):
                if filename.endswith('.jpg'):
                    frames.append(os.path.join(session_dir, filename))
            
            return frames
            
        except Exception as e:
            logger.error(f"Failed to get session frames: {e}")
            return []
    
    def cleanup_old_frames(self):
        """
        Delete frames older than cleanup_age_days
        Run this periodically as a background task
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=self.cleanup_age_days)
            deleted_count = 0
            
            for session_dir in os.listdir(self.proctoring_dir):
                session_path = os.path.join(self.proctoring_dir, session_dir)
                
                if not os.path.isdir(session_path):
                    continue
                
                for filename in os.listdir(session_path):
                    filepath = os.path.join(session_path, filename)
                    
                    # Get file modification time
                    mod_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                    
                    if mod_time < cutoff_time:
                        try:
                            os.remove(filepath)
                            deleted_count += 1
                            logger.info(f"Deleted old frame: {filepath}")
                        except Exception as e:
                            logger.error(f"Failed to delete frame: {e}")
            
            logger.info(f"Cleanup complete: {deleted_count} frames deleted")
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
    
    def schedule_cleanup(self, interval_hours: int = 24):
        """
        Schedule periodic cleanup of old frames
        
        Args:
            interval_hours: Cleanup interval in hours
        """
        def run_cleanup():
            while True:
                import time
                time.sleep(interval_hours * 3600)
                self.cleanup_old_frames()
        
        # Run cleanup in background thread
        cleanup_thread = threading.Thread(target=run_cleanup, daemon=True)
        cleanup_thread.start()
        logger.info(f"Frame cleanup scheduled every {interval_hours} hours")


# Lazy singleton
_proctoring_service = None

def get_proctoring_service(upload_base_path='backend/uploads'):
    global _proctoring_service
    if _proctoring_service is None:
        _proctoring_service = ProctoringService(upload_base_path)
    return _proctoring_service
