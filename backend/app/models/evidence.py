from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database.session import Base

class Evidence(Base):
    """SQLAlchemy model representing structured payment-risk evidence."""
    __tablename__ = "evidences"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False)
    evidence_id = Column(String(50), unique=True, index=True, nullable=False) # e.g. EV-101
    category = Column(String(50), nullable=False) # amount_deviation, velocity, geographic_mismatch, device_relationship, account_relationship, behavioral_anomaly, rule_violation, policy_match, model_signal
    severity = Column(String(20), nullable=False) # low, medium, high
    value = Column(String(255), nullable=True) # e.g. "4 failed attempts in 6 minutes"
    description = Column(Text, nullable=False)
    source = Column(String(100), nullable=False)
    confidence = Column(Float, default=1.0)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    supporting_entity = Column(String(100), nullable=True)
    supporting_transaction = Column(String(100), nullable=True)
    policy_reference = Column(String(100), nullable=True)

    # Relationships
    transaction = relationship("Transaction", back_populates="evidences")
