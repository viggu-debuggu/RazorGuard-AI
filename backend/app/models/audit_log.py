from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.database.session import Base

class AuditLog(Base):
    """SQLAlchemy model representing an auditable risk analysis/override state transition."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id", ondelete="CASCADE"), nullable=True)
    event = Column(String(50), nullable=False) # transaction_received, analysis_started, risk_calculated, decision_overridden, etc.
    description = Column(Text, nullable=False)
    actor = Column(String(100), nullable=False) # e.g. "System", "Orchestrator", "Analyst: email"
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    metadata_json = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    # Relationships
    transaction = relationship("Transaction", back_populates="audit_logs")
