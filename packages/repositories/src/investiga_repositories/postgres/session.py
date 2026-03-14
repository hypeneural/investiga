"""SQLAlchemy database session and engine configuration."""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from investiga_api.settings import settings


engine = create_engine(
    settings.database_url,
    echo=(settings.app_env == "development"),
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


def get_db():
    """Dependency for FastAPI: yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
