"""Database engine helpers for the platform backend."""

from sqlalchemy import Engine, create_engine


def create_database_engine(database_url: str) -> Engine:
    """Create a SQLAlchemy engine from the configured database URL."""
    return create_engine(database_url, pool_pre_ping=True)
