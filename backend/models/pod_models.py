from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class PODAlert(Base):
    __tablename__ = "pod_alerts"

    id = Column(Integer, primary_key=True)
    event_id = Column(String, index=True)
    home_team = Column(String)
    away_team = Column(String)
    league_name = Column(String)
    start_time = Column(DateTime)
    old_odds = Column(String)
    new_odds = Column(String)
    no_vig_price = Column(String)
    alert_timestamp = Column(DateTime, default=datetime.utcnow)
    is_dismissed = Column(Boolean, default=False)
    is_expired = Column(Boolean, default=False)
    
    # Relationships
    event_data = relationship("EventData", back_populates="alert", uselist=False)

class EventData(Base):
    __tablename__ = "event_data"

    id = Column(Integer, primary_key=True)
    alert_id = Column(Integer, ForeignKey("pod_alerts.id"))
    pinnacle_data = Column(JSON)
    betbck_data = Column(JSON)
    last_update = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    alert = relationship("PODAlert", back_populates="event_data")
    potential_bets = relationship("PotentialBet", back_populates="event_data")

class PotentialBet(Base):
    __tablename__ = "potential_bets"

    id = Column(Integer, primary_key=True)
    event_data_id = Column(Integer, ForeignKey("event_data.id"))
    market = Column(String)
    selection = Column(String)
    line = Column(String)
    ev = Column(Float)
    bet_odds = Column(Float)
    true_odds = Column(Float)
    is_placed = Column(Boolean, default=False)
    placed_at = Column(DateTime, nullable=True)
    
    # Relationships
    event_data = relationship("EventData", back_populates="potential_bets")

# Create tables
def init_db(engine):
    Base.metadata.create_all(engine) 