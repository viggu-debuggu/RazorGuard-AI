from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime
from app.database.session import Base


class GraphEdge(Base):
    """SQLAlchemy model representing a semantic relation in the payment network."""
    __tablename__ = "graph_edges"

    id = Column(Integer, primary_key=True, index=True)
    
    # Types: "User", "Transaction", "Card", "Device", "IP", "Merchant"
    source_type = Column(String(50), nullable=False)
    source_id = Column(String(50), nullable=False, index=True)
    
    # Relations: "INITIATED", "USED_CARD", "FROM_DEVICE", "FROM_IP", "TO_MERCHANT"
    relation = Column(String(50), nullable=False)
    
    target_type = Column(String(50), nullable=False)
    target_id = Column(String(50), nullable=False, index=True)
    
    weight = Column(Float, default=1.0, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
