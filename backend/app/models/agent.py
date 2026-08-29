import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float, JSON
from sqlalchemy.orm import relationship
from app.database.session import Base

try:
    from sqlalchemy.dialects.postgresql import JSONB
except ImportError:
    JSONB = None  # type: ignore


class AgentExecution(Base):
    """SQLAlchemy model tracking multi-agent investigation execution steps, duration, and consolidated evidence."""
    __tablename__ = "agent_executions"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True, index=True, nullable=False)
    
    transaction_id = Column(Integer, ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False)
    agents_used = Column(Text, nullable=False) # Comma-separated list of agents run
    reasoning_steps = Column(JSON().with_variant(JSONB, "postgresql"), default=list, nullable=False) # Serialized steps log
    evidence_retrieved = Column(Text, nullable=True) # Unified compiled evidence summary
    
    duration = Column(Float, default=0.0, nullable=False) # Processing duration in seconds
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    transaction = relationship("Transaction", back_populates="executions")


class AgentMemory(Base):
    """SQLAlchemy model representing individual agent memory instances, findings, and confidence weights."""
    __tablename__ = "agent_memories"

    id = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String(100), nullable=False, index=True)
    transaction_id = Column(Integer, nullable=False, index=True)
    
    reasoning = Column(Text, nullable=False)
    evidence = Column(Text, nullable=True)
    confidence = Column(Float, default=100.0, nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
