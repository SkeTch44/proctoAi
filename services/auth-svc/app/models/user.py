"""
User model — auth-svc owns this table.
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(150), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True)
    password_hash = Column(Text, nullable=False)
    role = Column(String(20), default="student")
    created_at = Column(DateTime, default=func.now())
    last_login = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
