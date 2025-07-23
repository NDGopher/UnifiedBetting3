from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from contextlib import contextmanager
import logging
from typing import Generator

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, database_url: str):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {str(e)}")
            raise
        finally:
            session.close()

    def init_db(self):
        """Initialize the database"""
        from .models.pod_models import Base
        Base.metadata.create_all(bind=self.engine)

# Create a singleton instance
db_manager = DatabaseManager("sqlite:///./betting_app.db")  # Will be configured from environment variables 