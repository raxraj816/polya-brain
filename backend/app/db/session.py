"""Database engine helpers for the platform backend."""

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def create_database_engine(database_url: str) -> Engine:
    """Create a SQLAlchemy engine from the configured database URL."""
    return create_engine(database_url, pool_pre_ping=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a synchronous SQLAlchemy session factory for local utilities."""
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
