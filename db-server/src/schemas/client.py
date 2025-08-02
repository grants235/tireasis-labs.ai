"""
Pydantic schemas for client models
"""
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ClientCreate(BaseModel):
    """Schema for creating a new client"""
    client_name: str
    api_key_hash: str
    he_context_public_key: str  # Base64 encoded
    he_scheme: str = 'CKKS'
    poly_modulus_degree: int = 8192
    scale: int = 1099511627776
    embedding_dim: int = 384
    max_embeddings_allowed: Optional[int] = 100000


class ClientUpdate(BaseModel):
    """Schema for updating a client"""
    client_name: Optional[str] = None
    is_active: Optional[bool] = None
    max_embeddings_allowed: Optional[int] = None


class ClientResponse(BaseModel):
    """Schema for client response"""
    client_id: uuid.UUID
    client_name: str
    he_scheme: str
    poly_modulus_degree: int
    scale: int
    embedding_dim: int
    max_embeddings_allowed: int
    created_at: datetime
    last_active_at: datetime
    is_active: bool
    total_embeddings: int
    total_searches: int

    class Config:
        from_attributes = True