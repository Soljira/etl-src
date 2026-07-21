from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
import logging

from src.config.settings import settings

logger = logging.getLogger(__name__)

# Create SQLAlchemy engine
engine = create_engine(settings.DATABASE_URL)

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for declarative models
Base = declarative_base()

def get_db_session():
    """Provides a transactional scope around a series of operations."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

def test_connection():
    """Test the database connection."""
    try:
        with engine.connect() as connection:
            logger.info("Successfully connected to the database.")
            return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False
