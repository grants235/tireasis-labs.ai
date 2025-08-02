"""
LSH related models
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, BYTEA

from ..core.database import Base


class LSHConfig(Base):
    """LSH configuration per client"""
    __tablename__ = "lsh_configs"
    
    config_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.client_id", ondelete="CASCADE"), nullable=False)
    
    num_tables = Column(Integer, nullable=False, default=20)
    hash_size = Column(Integer, nullable=False, default=16)
    num_candidates = Column(Integer, nullable=False, default=100)
    
    # Random planes for LSH (stored as serialized numpy array)
    random_planes = Column(BYTEA, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class LSHHash(Base):
    """LSH hash mappings (one row per hash table per embedding)"""
    __tablename__ = "lsh_hashes"
    
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.client_id", ondelete="CASCADE"), nullable=False, primary_key=True)
    embedding_id = Column(UUID(as_uuid=True), ForeignKey("embeddings.embedding_id", ondelete="CASCADE"), nullable=False, primary_key=True)
    table_index = Column(Integer, nullable=False, primary_key=True)  # Which hash table (0 to num_tables-1)
    hash_value = Column(Integer, nullable=False, primary_key=True)   # The hash value for this table