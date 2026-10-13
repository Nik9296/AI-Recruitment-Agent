"""Async SQLAlchemy engine and session factory."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config.settings import get_settings

engine: AsyncEngine | None = None
SessionLocal: async_sessionmaker[AsyncSession] | None = None


class DatabaseNotConfiguredError(RuntimeError):
    """Raised when DATABASE_URL is missing."""


def init_engine(database_url: str | None = None) -> None:
    global engine, SessionLocal
    url = database_url or get_settings().database_url
    if not url:
        raise DatabaseNotConfiguredError(
            "DATABASE_URL is not set. Configure it via environment variables."
        )
    engine = create_async_engine(url, pool_pre_ping=True)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def close_engine() -> None:
    global engine, SessionLocal
    if engine is not None:
        await engine.dispose()
    engine = None
    SessionLocal = None


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    if SessionLocal is None:
        raise DatabaseNotConfiguredError(
            "Database engine is not initialized. Set DATABASE_URL."
        )
    async with SessionLocal() as session:
        yield session
