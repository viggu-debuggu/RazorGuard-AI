from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.database.session import Base


class Transaction(Base):
    """SQLAlchemy model representing a payment transaction event."""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String(50), unique=True, index=True, nullable=False)
    user_id = Column(String(50), index=True, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False)
    
    # Device fingerprint & geolocation details
    device_fingerprint = Column(String(100), nullable=False)
    ip_address = Column(String(50), nullable=False)
    billing_country = Column(String(10), nullable=False)
    card_country = Column(String(10), nullable=False)
    card_present = Column(Boolean, default=False, nullable=False)
    
    # Merchant context
    merchant_id = Column(String(50), index=True, nullable=False)
    merchant_category = Column(String(50), nullable=False)
    
    # Flow statuses: "Pending", "Approved", "Blocked", "Escalated"
    status = Column(String(50), default="Pending", nullable=False)
    risk_score = Column(Float, default=0.0, nullable=False)
    
    timestamp = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    assessment = relationship("RiskAssessment", uselist=False, back_populates="transaction", cascade="all, delete-orphan")
    executions = relationship("AgentExecution", back_populates="transaction", cascade="all, delete-orphan")
    decisions = relationship("AnalystDecision", back_populates="transaction", cascade="all, delete-orphan")
    evidences = relationship("Evidence", back_populates="transaction", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="transaction", cascade="all, delete-orphan")
    submissions = relationship("MerchantSubmission", back_populates="transaction", cascade="all, delete-orphan")
