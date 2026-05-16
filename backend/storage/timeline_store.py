"""
Risk Timeline Storage for Explainability
Stores risk evolution over time for human review
"""

import sqlite3
from typing import List, Dict, Any
import logging
import os

logger = logging.getLogger(__name__)


class TimelineStore:
    """
    Store risk timeline for explainability
    Provides audit trail for human review
    """
    
    def __init__(self, db_path: str = "exam_platform.db"):
        """
        Initialize timeline store
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_table()
        logger.info(f"TimelineStore initialized: {db_path}")
    
    def _create_table(self):
        """Create timeline table if it doesn't exist"""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS risk_timeline (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                timestamp REAL NOT NULL,
                risk_score REAL NOT NULL,
                behavior_state TEXT NOT NULL,
                reason TEXT,
                patterns TEXT,
                violation_count INTEGER DEFAULT 0,
                session_duration REAL DEFAULT 0
            )
        """)
        
        # Create index for fast queries
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_student_time 
            ON risk_timeline (student_id, timestamp)
        """)
        
        self.conn.commit()
    
    def add_entry(self, student_id: str, explanation: Dict[str, Any]):
        """
        Add a timeline entry
        
        Args:
            student_id: Student identifier
            explanation: Explanation dictionary from StudentAgent
        """
        try:
            self.conn.execute("""
                INSERT INTO risk_timeline 
                (student_id, timestamp, risk_score, behavior_state, reason, patterns, violation_count, session_duration)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                student_id,
                explanation['timestamp'],
                explanation['risk_score'],
                explanation['behavior_state'],
                '; '.join(explanation['reasons']),
                ','.join(explanation['patterns_detected']),
                explanation['violation_count'],
                explanation['session_duration']
            ))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Failed to add timeline entry: {e}")
    
    def get_timeline(self, student_id: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Get full timeline for a student
        
        Args:
            student_id: Student identifier
            limit: Maximum number of entries
        
        Returns:
            List of timeline entries
        """
        cursor = self.conn.execute("""
            SELECT timestamp, risk_score, behavior_state, reason, patterns, violation_count
            FROM risk_timeline
            WHERE student_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (student_id, limit))
        
        return [
            {
                "t": row[0],
                "risk": row[1],
                "state": row[2],
                "reason": row[3],
                "patterns": row[4].split(',') if row[4] else [],
                "violations": row[5]
            }
            for row in cursor.fetchall()
        ]
    
    def get_summary(self, student_id: str) -> Dict[str, Any]:
        """
        Get summary statistics for a student
        
        Args:
            student_id: Student identifier
        
        Returns:
            Summary dictionary
        """
        cursor = self.conn.execute("""
            SELECT 
                COUNT(*) as total_entries,
                MAX(risk_score) as max_risk,
                AVG(risk_score) as avg_risk,
                MAX(violation_count) as total_violations,
                MAX(session_duration) as session_duration
            FROM risk_timeline
            WHERE student_id = ?
        """, (student_id,))
        
        row = cursor.fetchone()
        if row:
            return {
                "total_entries": row[0],
                "max_risk": round(row[1] or 0, 2),
                "avg_risk": round(row[2] or 0, 2),
                "total_violations": row[3] or 0,
                "session_duration": round(row[4] or 0, 1)
            }
        return {}
    
    def clear_student(self, student_id: str):
        """
        Clear timeline for a student (e.g., after exam ends)
        
        Args:
            student_id: Student identifier
        """
        self.conn.execute("DELETE FROM risk_timeline WHERE student_id = ?", (student_id,))
        self.conn.commit()
        logger.info(f"Cleared timeline for {student_id}")
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
