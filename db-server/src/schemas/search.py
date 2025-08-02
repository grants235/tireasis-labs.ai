"""
Pydantic schemas for search models
"""
import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class SearchRequestCreate(BaseModel):
    """Schema for creating a search request"""
    client_id: uuid.UUID
    encrypted_query: str  # Base64 encoded
    lsh_hashes: List[int]
    top_k: int
    rerank_candidates: int


class SearchRequestUpdate(BaseModel):
    """Schema for updating search request with performance metrics"""
    candidates_found: Optional[int] = None
    candidates_checked: Optional[int] = None
    lsh_time_ms: Optional[int] = None
    he_compute_time_ms: Optional[int] = None
    total_time_ms: Optional[int] = None
    results_returned: Optional[int] = None


class SearchRequestResponse(BaseModel):
    """Schema for search request response"""
    search_id: uuid.UUID
    client_id: uuid.UUID
    top_k: int
    rerank_candidates: int
    candidates_found: Optional[int]
    candidates_checked: Optional[int]
    lsh_time_ms: Optional[int]
    he_compute_time_ms: Optional[int]
    total_time_ms: Optional[int]
    results_returned: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True