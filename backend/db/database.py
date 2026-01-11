import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict

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
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
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
    def user_exists(self, username: str, email: str) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM users WHERE username = ? OR email = ?",
            (username, email)
        )
        exists = cursor.fetchone() is not None
        conn.close()
        return exists

    def create_user(
        self,
        username: str,
        email: str,
        password_hash: str,
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