from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database.session import Base


class MerchantSubmission(Base):
    """SQLAlchemy model representing merchant-submitted evidence documents and notes."""
    __tablename__ = "merchant_submissions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False)
    notes = Column(Text, nullable=False)
    document_url = Column(String(255), nullable=True)
    target_category = Column(String(50), nullable=True)
    submitted_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    status = Column(String(50), default="Submitted", nullable=False)

    # Relationships
    transaction = relationship("Transaction", back_populates="submissions")
