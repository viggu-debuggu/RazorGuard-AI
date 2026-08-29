import os
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, PickleType
from sqlalchemy.orm import relationship
from app.database.session import Base

# Dynamic fallback to Pickletype for SQLite local test compliance
if "postgresql" in os.getenv("DATABASE_URL", ""):
    from pgvector.sqlalchemy import Vector
    EmbeddingType = Vector(384)
else:
    EmbeddingType = PickleType


class PolicyDocument(Base):
    """SQLAlchemy model representing uploaded risk policy and regulatory manuals."""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    checksum = Column(String(64), unique=True, nullable=False) # SHA256 file verification
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    chunks = relationship("PolicyChunk", back_populates="document", cascade="all, delete-orphan")


class PolicyChunk(Base):
    """SQLAlchemy model representing individual document chunks with pgvector/Pickle embeddings."""
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    
    # 384-dimensional dense embedding vectors (Vector on Postgres, Pickle on SQLite)
    embedding = Column(EmbeddingType, nullable=False)

    # Relationships
    document = relationship("PolicyDocument", back_populates="chunks")
