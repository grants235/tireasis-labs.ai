"""
Client model for secure search database
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, BIGINT
from sqlalchemy.dialects.postgresql import UUID, BYTEA

from ..core.database import Base


class Client(Base):
    """Client table for storing authenticated clients and their HE contexts"""
    __tablename__ = "clients"
    
    client_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    client_name = Column(String(255), nullable=False)
    api_key_hash = Column(String(255), nullable=False, unique=True)
    
    # HE Context Information
    he_context_public_key = Column(BYTEA, nullable=False)
    he_scheme = Column(String(50), nullable=False, default='CKKS')
    poly_modulus_degree = Column(Integer, nullable=False, default=8192)
    scale = Column(BIGINT, nullable=False, default=1099511627776)
    
    # Configuration
    embedding_dim = Column(Integer, nullable=False, default=384)
    max_embeddings_allowed = Column(Integer, default=100000)
    
    # Timestamps and status
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Usage statistics
    total_embeddings = Column(Integer, default=0)
    total_searches = Column(Integer, default=0)