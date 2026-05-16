from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20
        )
    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autocommit=False, autoflush=False)
    return _SessionLocal


def get_db() -> Session:
    factory = get_session_factory()
    db = factory()
    try:
        yield db
    finally:
        db.close()
