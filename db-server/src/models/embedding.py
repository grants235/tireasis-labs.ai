"""
Embedding related models
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, BYTEA

from ..core.database import Base


class Embedding(Base):
    """Main embeddings table for encrypted vectors"""
    __tablename__ = "embeddings"
    
    embedding_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.client_id", ondelete="CASCADE"), nullable=False)
    
    # User-provided ID (optional)
    external_id = Column(String(255))
    
    # Encrypted embedding data
    encrypted_vector = Column(BYTEA, nullable=False)
    vector_size_bytes = Column(Integer, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    accessed_at = Column(DateTime, default=datetime.utcnow)
    access_count = Column(Integer, default=0)
    
    # Soft delete support
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime)


class EmbeddingMetadata(Base):
    """Flexible metadata storage using JSONB"""
    __tablename__ = "embedding_metadata"
    
    embedding_id = Column(UUID(as_uuid=True), ForeignKey("embeddings.embedding_id", ondelete="CASCADE"), primary_key=True)
    metadata_json = Column("metadata", JSON, nullable=False, default={})