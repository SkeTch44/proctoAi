import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import json

from werkzeug.security import check_password_hash
from backend.models.schema import db, User, Exam, Session, ProctoringEvent

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Comprehensive database manager for the exam platform using SQLAlchemy ORM.
    Handles CRUD operations for users, exams, sessions, proctoring.
    """

    def __init__(self, database_url: str):
        # database_url is kept for backward API compatibility but managed by Flask-SQLAlchemy
        self.db_path = database_url.replace("sqlite:///", "")

    def init_database(self) -> bool:
        # Tables are created via db.create_all() in app.py now
        logger.info("Database initialized successfully via SQLAlchemy")
        return True

    # ---------- USER OPERATIONS ----------
    def user_exists(self, username: str, email: Optional[str] = None) -> bool:
        query = User.query.filter(User.username == username)
        if email:
            query = query.filter((User.username == username) | (User.email == email))
        return query.first() is not None

    def create_user(
        self,
        username: str,
        password_hash: str,
        email: Optional[str] = None,
        role: str = "student"
    ) -> Optional[int]:
        try:
            user = User(username=username, email=email, password_hash=password_hash, role=role)
            db.session.add(user)
            db.session.commit()
            logger.info(f"User created: {username} (ID {user.id})")
            return user.id
        except Exception as e:
            db.session.rollback()
            logger.error(f"User creation failed: {e}")
            return None

    def get_user_by_username(self, username: str) -> Optional[User]:
        return User.query.filter_by(username=username).first()

    def authenticate_user(self, identifier: str, password: str) -> Optional[User]:
        try:
            user = User.query.filter((User.username == identifier) | (User.email == identifier)).first()
            if not user:
                return None

            # Account locked?
            if user.locked_until and datetime.utcnow() < user.locked_until:
                logger.warning(f"Locked account login attempt: {identifier}")
                return None

            # Password check
            if check_password_hash(user.password_hash, password):
                user.login_attempts = 0
                user.locked_until = None
                user.last_login = datetime.utcnow()
                db.session.commit()
                return user

            # Failed login
            user.login_attempts += 1
            if user.login_attempts >= 5:
                user.locked_until = datetime.utcnow() + timedelta(minutes=30)
            
            db.session.commit()
            logger.warning(f"Failed login {identifier} (attempt {user.login_attempts})")
            return None

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None

    # ---------- EXAM OPERATIONS ----------
    def create_exam(self, title: str, description: str, questions: list, duration: int, created_by: int) -> Optional[int]:
        try:
            exam = Exam(
                title=title, 
                description=description, 
                questions=json.dumps(questions), 
                duration=duration, 
                created_by=created_by
            )
            db.session.add(exam)
            db.session.commit()
            return exam.id
        except Exception as e:
            db.session.rollback()
            logger.error(f"Create exam failed: {e}")
            return None

    def get_all_exams(self) -> List[Exam]:
        return Exam.query.all()

    def get_exam_by_id(self, exam_id: int) -> Optional[Exam]:
        return Exam.query.get(exam_id)

    # ---------- SESSION OPERATIONS ----------
    def create_session(self, exam_id: int, user_id: int) -> Optional[int]:
        try:
            session = Session(exam_id=exam_id, user_id=user_id, status='active')
            db.session.add(session)
            db.session.commit()
            return session.id
        except Exception as e:
            db.session.rollback()
            logger.error(f"Create session failed: {e}")
            return None

    def get_session(self, session_id: int, user_id: Optional[int] = None) -> Optional[Session]:
        query = Session.query.filter_by(id=session_id)
        if user_id:
            query = query.filter_by(user_id=user_id)
        return query.first()

    def get_full_session_details(self, session_id: int, user_id: int) -> Optional[dict]:
        # Returns dict for compatibility with report generators and direct API returns
        session = Session.query.filter_by(id=session_id, user_id=user_id).first()
        if session and session.exam:
            return {
                'id': session.id,
                'user_id': session.user_id,
                'exam_id': session.exam_id,
                'answers': session.answers,
                'questions': session.exam.questions,
                'score': session.score,
                'status': session.status,
                'started_at': session.started_at,
                'completed_at': session.completed_at
            }
        return None

    def update_session_answers(self, session_id: int, answers: dict):
        try:
            session = Session.query.get(session_id)
            if session:
                session.answers = json.dumps(answers)
                db.session.commit()
        except BaseException as e:
            db.session.rollback()
            logger.error(e)

    def complete_session(self, session_id: int, score: float):
        try:
            session = Session.query.get(session_id)
            if session:
                session.completed_at = datetime.utcnow()
                session.status = 'completed'
                session.score = score
                db.session.commit()
        except BaseException as e:
            db.session.rollback()

    def update_suspicion_score(self, session_id: int, score_increase: int):
        try:
            session = Session.query.get(session_id)
            if session:
                session.suspicion_score += score_increase
                db.session.commit()
        except BaseException as e:
            db.session.rollback()

    def get_active_sessions_with_details(self) -> List[Dict]:
        sessions = Session.query.filter_by(status='active').all()
        return [{
            'id': s.id,
            'username': s.user.username,
            'title': s.exam.title,
            'suspicion_score': s.suspicion_score,
            'started_at': s.started_at.isoformat() if s.started_at else None
        } for s in sessions if s.user and s.exam]

    # ---------- PROCTORING OPERATIONS ----------
    def log_proctoring_event(self, session_id: int, event_type: str, severity: str, details: str):
        try:
            event = ProctoringEvent(
                session_id=session_id,
                event_type=event_type,
                severity=severity,
                details=details
            )
            db.session.add(event)
            db.session.commit()
        except BaseException as e:
            db.session.rollback()
            logger.error(e)

    def get_recent_alerts(self, limit: int = 20) -> List[Dict]:
        events = ProctoringEvent.query.order_by(ProctoringEvent.timestamp.desc()).limit(limit).all()
        return [{
            'event_type': e.event_type,
            'severity': e.severity,
            'timestamp': e.timestamp.isoformat() if e.timestamp else None,
            'username': e.session.user.username if e.session and e.session.user else 'Unknown'
        } for e in events]
