from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

Base = declarative_base()

class HighEVAlert(Base):
    __tablename__ = "high_ev_alerts"
    
    id = Column(Integer, primary_key=True)
    event_id = Column(String(50), index=True)
    sport = Column(String(50))
    away_team = Column(String(100))
    home_team = Column(String(100))
    ev_percentage = Column(Float)
    bet_type = Column(String(50))
    odds = Column(String(50))
    nvp = Column(String(50))
    alert_data = Column(JSON)  # Full alert data
    created_at = Column(DateTime, default=datetime.utcnow)
    processed = Column(String(20), default="pending")  # pending, processed, failed

# Database setup
def setup_database():
    # Create database file in the backend directory
    db_path = os.path.join(os.path.dirname(__file__), 'high_ev_alerts.db')
    engine = create_engine(f'sqlite:///{db_path}')
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)

# Create session factory - lazy initialization
SessionLocal = None

def get_session():
    global SessionLocal
    if SessionLocal is None:
        SessionLocal = setup_database()
    return SessionLocal() 