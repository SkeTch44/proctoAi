from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


_async_engine = None
_async_session_factory = None


def _get_async_url(url: str) -> str:
    """Convert a standard postgresql:// URL to use the asyncpg driver."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql+asyncpg://"):
        return url
    return url


def get_async_engine():
    global _async_engine
    if _async_engine is None:
        settings = get_settings()
        _async_engine = create_async_engine(
            _get_async_url(settings.DATABASE_URL),
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            pool_recycle=300,
        )
    return _async_engine


def get_async_session_factory():
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            bind=get_async_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_factory


async def get_db() -> AsyncSession:
    factory = get_async_session_factory()
    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()
