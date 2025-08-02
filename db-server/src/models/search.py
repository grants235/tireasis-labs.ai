"""
Search related models
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, BYTEA, ARRAY

from ..core.database import Base


class SearchRequest(Base):
    """Search request logging"""
    __tablename__ = "search_requests"
    
    search_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.client_id", ondelete="CASCADE"), nullable=False)
    
    # Search parameters
    encrypted_query = Column(BYTEA, nullable=False)
    lsh_hashes = Column(ARRAY(Integer), nullable=False)
    top_k = Column(Integer, nullable=False)
    rerank_candidates = Column(Integer, nullable=False)
    
    # Performance metrics
    candidates_found = Column(Integer)
    candidates_checked = Column(Integer)
    lsh_time_ms = Column(Integer)
    he_compute_time_ms = Column(Integer)
    total_time_ms = Column(Integer)
    
    # Results summary
    results_returned = Column(Integer)
    
    created_at = Column(DateTime, default=datetime.utcnow)