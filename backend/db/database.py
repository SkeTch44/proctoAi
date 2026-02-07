import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
from werkzeug.security import check_password_hash, generate_password_hash

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, database_url: str):
        if database_url.startswith("sqlite:///"):
            self.db_path = database_url.replace("sqlite:///", "", 1)
        else:
            self.db_path = database_url

    def get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def migrate_schema(self):
        conn = self.get_connection()
        try:
            # ADD full_name FIRST (CRITICAL)
            try:
                conn.execute("ALTER TABLE users ADD COLUMN full_name TEXT;")
                print("✅ Added full_name column")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE users ADD COLUMN password_changed_at TIMESTAMP;")
                print("✅ Added password_changed_at column")
            except sqlite3.OperationalError:
                pass

            for stmt in [
                "ALTER TABLE users ADD COLUMN phone TEXT;",
                "ALTER TABLE users ADD COLUMN institution TEXT;",
                "ALTER TABLE users ADD COLUMN program TEXT;",
                "ALTER TABLE users ADD COLUMN year TEXT;",
                "ALTER TABLE users ADD COLUMN avatar_url TEXT;",
                "ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1;",
                "ALTER TABLE users ADD COLUMN login_attempts INTEGER DEFAULT 0;",
                "ALTER TABLE users ADD COLUMN locked_until TIMESTAMP;",
                "ALTER TABLE users ADD COLUMN last_login TIMESTAMP;",
                "ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;",
                "ALTER TABLE users ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;",
            ]:
                try:
                    conn.execute(stmt)
                except sqlite3.OperationalError:
                    pass
            conn.execute("""
            CREATE TABLE IF NOT EXISTS exams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                max_score INTEGER NOT NULL,
                exam_date TIMESTAMP,
                status TEXT DEFAULT 'Completed' CHECK(status IN ('Completed', 'Pending', 'Failed'))
                 );
                """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS exam_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    exam_id INTEGER NOT NULL,
                    score INTEGER NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('Pass', 'Fail')),
                    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (exam_id) REFERENCES exams(id)
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS support_tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    type TEXT NOT NULL CHECK(type IN ('technical', 'policy', 'general')),
                    subject TEXT NOT NULL,
                    message TEXT NOT NULL,
                    status TEXT DEFAULT 'open' CHECK(status IN ('open', 'in_progress', 'resolved', 'closed')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
                    category TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    message TEXT NOT NULL,
                    suggestions TEXT,
                    status TEXT DEFAULT 'received' CHECK(status IN ('received', 'reviewed', 'implemented')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );
            """)
            conn.execute("UPDATE users SET is_active = 1 WHERE is_active IS NULL;")
            conn.execute("UPDATE users SET login_attempts = 0 WHERE login_attempts IS NULL;")
            conn.commit()
            print("✅ Migration complete")
            print("✅ Exam results tables created")
            print("✅ Support tickets table created") 
            print("✅ Feedback table created")
        finally:
            conn.close()

    def init_database(self) -> bool:
        conn = self.get_connection()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    full_name TEXT NOT NULL,  -- REQUIRED
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'student' CHECK (role IN ('admin', 'student', 'teacher')),
                    phone TEXT, institution TEXT, program TEXT, year TEXT, avatar_url TEXT,
                    is_active INTEGER DEFAULT 1, login_attempts INTEGER DEFAULT 0, locked_until TIMESTAMP,
                    last_login TIMESTAMP, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"DB init failed: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def create_user(self, username: str, email: str, password: str, role: str = "student", full_name: str = None) -> Optional[int]:
        conn = self.get_connection()
        try:
            password_hash = generate_password_hash(password)
            cur = conn.execute(
                "INSERT INTO users (username, full_name, email, password_hash, role) VALUES (?, ?, ?, ?, ?)",
                (username, full_name, email, password_hash, role)
            )
            conn.commit()
            print(f"✅ Created user: {username} (full_name: {full_name})")
            return cur.lastrowid
        except Exception as e:
            print(f"Create error: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()

    def authenticate_user(self, identifier: str, password: str) -> Optional[Dict]:
        conn = self.get_connection()
        try:
            row = conn.execute("SELECT * FROM users WHERE username = ? OR email = ?", (identifier, identifier)).fetchone()
            if not row:
                return None
            user = dict(row)
            
            if user["locked_until"] and datetime.utcnow() < datetime.fromisoformat(user["locked_until"]):
                return None

            if check_password_hash(user["password_hash"], password):
                conn.execute("UPDATE users SET login_attempts = 0, locked_until = NULL, last_login = CURRENT_TIMESTAMP WHERE id = ?", (user["id"],))
                conn.commit()
                user.pop("password_hash", None)
                user.pop("login_attempts", None)
                user.pop("locked_until", None)
                return user

            attempts = user["login_attempts"] + 1
            locked_until = (datetime.utcnow() + timedelta(minutes=30)).isoformat() if attempts >= 5 else None
            conn.execute("UPDATE users SET login_attempts = ?, locked_until = ? WHERE id = ?", (attempts, locked_until, user["id"]))
            conn.commit()
            return None
        finally:
            conn.close()

    def get_current_user(self, user_id: int) -> Optional[Dict]:
        conn = self.get_connection()
        try:
            row = conn.execute("""
                SELECT id, username, full_name, email, role, phone, institution, 
                       program, year, last_login, password_changed_at 
                FROM users WHERE id = ?
            """, (user_id,)).fetchone()
            if row:
                user = dict(row)
                user["name"] = user["full_name"] or user["username"]
                return user
            return None
        finally:
            conn.close()

    def update_student_profile(self, user_id: int, data: Dict) -> bool:
        conn = self.get_connection()
        try:
            conn.execute("""
                UPDATE users SET 
                    full_name = COALESCE(?, full_name),
                    phone = COALESCE(?, phone),
                    institution = COALESCE(?, institution),
                    program = COALESCE(?, program),
                    year = COALESCE(?, year),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                data.get("fullName"),
                data.get("phone"),
                data.get("institution"),
                data.get("program"),
                data.get("year"),
                user_id
            ))
            conn.commit()
            return True
        except Exception as e:
            print(f"Update error: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def change_password(self, user_id: int, current: str, new: str) -> bool:
        conn = self.get_connection()
        try:
            row = conn.execute(
                "SELECT password_hash FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
    
            if not row or not check_password_hash(row["password_hash"], current):
                return False
    
            new_hash = generate_password_hash(new)
            conn.execute("""
                UPDATE users 
                SET password_hash = ?, 
                    updated_at = CURRENT_TIMESTAMP,
                    password_changed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (new_hash, user_id))
            conn.commit()
            return True
        finally:
            conn.close()
            
    def get_student_results(self, user_id: int) -> list:
        conn = self.get_connection()
        try:
            results = conn.execute("""
                SELECT 
                    er.id, er.score, er.status, er.completed_at,
                    e.name, e.max_score, e.exam_date
                FROM exam_results er
                JOIN exams e ON er.exam_id = e.id
                WHERE er.user_id = ? 
                ORDER BY er.completed_at DESC
                LIMIT 10
            """, (user_id,)).fetchall()
        
            return [dict(row) for row in results]
        finally:
            conn.close()

    def get_student_stats(self, user_id: int) -> Dict:
        conn = self.get_connection()
        try:
            stats = conn.execute("""
                SELECT 
                    COUNT(*) as total_exams,
                    AVG(er.score * 1.0) as avg_score,
                    SUM(CASE WHEN er.status = 'Pass' THEN 1 ELSE 0 END) as passed_count
                FROM exam_results er
                WHERE er.user_id = ?
            """, (user_id,)).fetchone()
            
            return dict(stats) if stats else {"total_exams": 0, "avg_score": 0, "passed_count": 0}
        finally:
            conn.close()
            
    def create_support_ticket(self, user_id: int, ticket_data: Dict) -> int:
        conn = self.get_connection()
        try:
            cur = conn.execute("""
                INSERT INTO support_tickets (user_id, type, subject, message)
                VALUES (?, ?, ?, ?)
            """, (
                user_id,
                ticket_data["type"],
                ticket_data["subject"],
                ticket_data["message"]
            ))
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()
            
    def get_user_tickets(self, user_id: int) -> list:
        conn = self.get_connection()
        try:
            tickets = conn.execute("""
                SELECT * FROM support_tickets 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT 10
            """, (user_id,)).fetchall()
            return [dict(row) for row in tickets]
        finally:
            conn.close()
            
    def submit_feedback(self, user_id: int, feedback_data: Dict) -> int:
        conn = self.get_connection()
        try:
            cur = conn.execute("""
                INSERT INTO feedback (user_id, rating, category, subject, message, suggestions)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                feedback_data["rating"],
                feedback_data["category"],
                feedback_data["subject"],
                feedback_data["message"],
                feedback_data.get("suggestions", "")
            ))
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()
            
    def get_user_feedback(self, user_id: int) -> list:
        conn = self.get_connection()
        try:
            feedback = conn.execute("""
                SELECT * FROM feedback 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT 10
            """, (user_id,)).fetchall()
            return [dict(row) for row in feedback]
        finally:
            conn.close()
            
    def get_student_dashboard_stats(self, user_id: int) -> Dict:
        conn = self.get_connection()
        try:
            # Enrolled exams count
            enrolled = conn.execute("""
                SELECT COUNT(*) FROM exam_rooms er
                JOIN exams e ON er.exam_id = e.id
                WHERE er.user_id = ? AND er.status IN ('Ready', 'In Progress')
            """, (user_id,)).fetchone()[0]
        
            # Upcoming exams (next 7 days)
            upcoming = conn.execute("""
                SELECT COUNT(*) FROM exam_rooms er
                JOIN exams e ON er.exam_id = e.id
                WHERE er.user_id = ? AND date(e.exam_date) >= date('now') 
                AND date(e.exam_date) <= date('now', '+7 days')
            """, (user_id,)).fetchone()[0]
        
            # Notifications (implement notifications table later)
            otifications = 0
        
            return {
                "enrolled_exams": enrolled,
                "upcoming_exams": upcoming,
                "notifications": notifications
            }
        finally:
            conn.close()
