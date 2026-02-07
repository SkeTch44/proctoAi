import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import json

from werkzeug.security import check_password_hash

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Comprehensive database manager for the exam platform
    Handles CRUD operations for users, exams, sessions, proctoring
    """

    def __init__(self, database_url: str):
        self.db_path = database_url.replace("sqlite:///", "")

    # ---------- CONNECTION ----------
    def get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    # ---------- INIT ----------
    def init_database(self) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT DEFAULT 'student'
                        CHECK (role IN ('student', 'teacher', 'admin')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    login_attempts INTEGER DEFAULT 0,
                    locked_until TIMESTAMP
                )
            """)
            
            # Exams table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS exams (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    questions TEXT NOT NULL,
                    duration INTEGER DEFAULT 3600,
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (created_by) REFERENCES users (id)
                )
            ''')
            
            # Sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    exam_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    answers TEXT,
                    score REAL DEFAULT 0,
                    suspicion_score INTEGER DEFAULT 0,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    status TEXT DEFAULT 'active',
                    FOREIGN KEY (exam_id) REFERENCES exams (id),
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Proctoring events table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS proctoring_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    details TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions (id)
                )
            ''')

            conn.commit()
            logger.info("Database initialized successfully")
            return True
        except Exception as e:
            conn.rollback()
            logger.error(f"Database init failed: {e}")
            return False
        finally:
            conn.close()

    # ---------- USER OPERATIONS ----------
    def user_exists(self, username: str, email: Optional[str] = None) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        if email:
            cursor.execute(
                "SELECT id FROM users WHERE username = ? OR email = ?",
                (username, email)
            )
        else:
            cursor.execute(
                "SELECT id FROM users WHERE username = ?",
                (username,)
            )
        exists = cursor.fetchone() is not None
        conn.close()
        return exists

    def create_user(
        self,
        username: str,
        password_hash: str,
        email: Optional[str] = None,
        role: str = "student"
    ) -> Optional[int]:

        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, role)
                VALUES (?, ?, ?, ?)
            """, (username, email, password_hash, role))
            conn.commit()
            user_id = cursor.lastrowid
            logger.info(f"User created: {username} (ID {user_id})")
            return user_id
        except Exception as e:
            conn.rollback()
            logger.error(f"User creation failed: {e}")
            return None
        finally:
            conn.close()

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, password_hash, role FROM users WHERE username = ?', (username,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return dict(row)
        return None

    def authenticate_user(self, identifier: str, password: str) -> Optional[Dict]:
        """
        identifier = username OR email
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT *
                FROM users
                WHERE username = ? OR email = ?
            """, (identifier, identifier))

            row = cursor.fetchone()
            if not row:
                return None

            user = dict(row)

            # Account locked?
            if user["locked_until"]:
                locked_until = datetime.fromisoformat(user["locked_until"])
                if datetime.utcnow() < locked_until:
                    logger.warning(f"Locked account login attempt: {identifier}")
                    return None

            # Password check
            if check_password_hash(user["password_hash"], password):
                cursor.execute("""
                    UPDATE users
                    SET login_attempts = 0,
                        locked_until = NULL,
                        last_login = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (user["id"],))
                conn.commit()

                # Remove sensitive fields
                user.pop("password_hash")
                user.pop("login_attempts")
                user.pop("locked_until")
                return user

            # Failed login
            attempts = user["login_attempts"] + 1
            lock_time = None
            if attempts >= 5:
                lock_time = (datetime.utcnow() + timedelta(minutes=30)).isoformat()

            cursor.execute("""
                UPDATE users
                SET login_attempts = ?, locked_until = ?
                WHERE id = ?
            """, (attempts, lock_time, user["id"]))
            conn.commit()

            logger.warning(f"Failed login {identifier} (attempt {attempts})")
            return None

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None
        finally:
            conn.close()

    # ---------- EXAM OPERATIONS ----------
    def create_exam(self, title: str, description: str, questions: list, duration: int, created_by: int) -> Optional[int]:
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                'INSERT INTO exams (title, description, questions, duration, created_by) VALUES (?, ?, ?, ?, ?)',
                (title, description, json.dumps(questions), duration, created_by)
            )
            conn.commit()
            exam_id = cursor.lastrowid
            return exam_id
        except Exception as e:
            logger.error(f"Create exam failed: {e}")
            return None
        finally:
            conn.close()

    def get_all_exams(self) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, title, description, duration FROM exams')
        exams = cursor.fetchall()
        conn.close()
        
        result = []
        for exam in exams:
            result.append({
                'id': exam['id'],
                'title': exam['title'],
                'description': exam['description'],
                'duration': exam['duration']
            })
        return result

    def get_exam_by_id(self, exam_id: int) -> Optional[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, title, questions, duration FROM exams WHERE id = ?', (exam_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return dict(row)
        return None

    # ---------- SESSION OPERATIONS ----------
    def create_session(self, exam_id: int, user_id: int) -> Optional[int]:
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO sessions (exam_id, user_id, status) VALUES (?, ?, 'active')",
                (exam_id, user_id)
            )
            session_id = cursor.lastrowid
            conn.commit()
            return session_id
        except Exception as e:
            logger.error(f"Create session failed: {e}")
            return None
        finally:
            conn.close()

    def get_session(self, session_id: int, user_id: Optional[int] = None) -> Optional[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM sessions WHERE id = ?"
        params = [session_id]
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
            
        cursor.execute(query, tuple(params))
        row = cursor.fetchone()
        conn.close()
        if row:
            return dict(row)
        return None

    def get_full_session_details(self, session_id: int, user_id: int) -> Optional[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT s.answers, e.questions 
            FROM sessions s 
            JOIN exams e ON s.exam_id = e.id 
            WHERE s.id = ? AND s.user_id = ?
        ''', (session_id, user_id))
        row = cursor.fetchone()
        conn.close()
        if row:
            return dict(row)
        return None

    def update_session_answers(self, session_id: int, answers: dict):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE sessions SET answers = ? WHERE id = ?', (json.dumps(answers), session_id))
        conn.commit()
        conn.close()

    def complete_session(self, session_id: int, score: float):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE sessions 
            SET completed_at = CURRENT_TIMESTAMP, status = 'completed', score = ?
            WHERE id = ?
        ''', (score, session_id))
        conn.commit()
        conn.close()

    def update_suspicion_score(self, session_id: int, score_increase: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE sessions SET suspicion_score = suspicion_score + ? WHERE id = ?',
            (score_increase, session_id)
        )
        conn.commit()
        conn.close()
        
    def get_active_sessions_with_details(self) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT s.id, u.username, e.title, s.suspicion_score, s.started_at
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            JOIN exams e ON s.exam_id = e.id
            WHERE s.status = 'active'
        ''')
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    # ---------- PROCTORING OPERATIONS ----------
    def log_proctoring_event(self, session_id: int, event_type: str, severity: str, details: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO proctoring_events (session_id, event_type, severity, details) VALUES (?, ?, ?, ?)',
            (session_id, event_type, severity, details)
        )
        conn.commit()
        conn.close()

    def get_recent_alerts(self, limit: int = 20) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f'''
            SELECT pe.event_type, pe.severity, pe.timestamp, u.username
            FROM proctoring_events pe
            JOIN sessions s ON pe.session_id = s.id
            JOIN users u ON s.user_id = u.id
            ORDER BY pe.timestamp DESC
            LIMIT {limit}
        ''')
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
