from datetime import datetime
# pyrefly: ignore [missing-import]
from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import relationship
from ..database.session import Base


class AnalystDecision(Base):
    """SQLAlchemy model logging decisions and validation justifications from human analysts."""
    __tablename__ = "analyst_decisions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False)
    analyst_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Decisions: "Approve", "Block", "Escalate"
    action = Column(String(50), nullable=False)
    notes = Column(Text, nullable=True) # Text reasoning submitted by the analyst
    
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    transaction = relationship("Transaction", back_populates="decisions")
    analyst = relationship("User", back_populates="decisions")
