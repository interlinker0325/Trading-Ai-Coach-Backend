from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Create database engine with SSL handling
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=300,    # Recycle connections every 5 minutes
    pool_size=5,         # Number of connections to maintain
    max_overflow=10,     # Additional connections when needed
    connect_args={
        "sslmode": "require",  # Force SSL connection
        "sslcert": None,       # No client certificate
        "sslkey": None,        # No client key
        "sslrootcert": None    # No root certificate
    }
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()


def get_db():
    """Dependency to get database session (for FastAPI dependency injection)"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session():
    """
    Get a database session for use in Celery tasks or other non-FastAPI contexts.
    Returns a session that must be closed manually.
    """
    return SessionLocal()