from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database.session import Base


class RiskAssessment(Base):
    """SQLAlchemy model representing a detailed multi-metric risk computation."""
    __tablename__ = "risk_assessments"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    # Mathematical score breakdowns
    overall_score = Column(Float, nullable=False)
    classification = Column(String(50), nullable=False) # Safe, Suspicious, High Risk
    
    ml_score = Column(Float, default=0.0, nullable=False)
    rule_score = Column(Float, default=0.0, nullable=False)
    graph_score = Column(Float, default=0.0, nullable=False)
    policy_score = Column(Float, default=0.0, nullable=False)
    
    explanation = Column(Text, nullable=True) # Detailed Markdown explanation
    analyzed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    transaction = relationship("Transaction", back_populates="assessment")
