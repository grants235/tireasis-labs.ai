"""
Pydantic schemas for embedding models
"""
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel


class EmbeddingCreate(BaseModel):
    """Schema for creating an embedding"""
    client_id: uuid.UUID
    external_id: Optional[str] = None
    encrypted_vector: str  # Base64 encoded
    vector_size_bytes: int
    metadata: Optional[Dict[str, Any]] = None


class EmbeddingUpdate(BaseModel):
    """Schema for updating an embedding"""
    external_id: Optional[str] = None
    is_deleted: Optional[bool] = None


class EmbeddingResponse(BaseModel):
    """Schema for embedding response"""
    embedding_id: uuid.UUID
    client_id: uuid.UUID
    external_id: Optional[str]
    vector_size_bytes: int
    created_at: datetime
    accessed_at: datetime
    access_count: int
    is_deleted: bool

    class Config:
        from_attributes = True


class EmbeddingMetadataCreate(BaseModel):
    """Schema for creating embedding metadata"""
    embedding_id: uuid.UUID
    metadata: Dict[str, Any]


class EmbeddingMetadataResponse(BaseModel):
    """Schema for embedding metadata response"""
    embedding_id: uuid.UUID
    metadata_json: Dict[str, Any]

    class Config:
        from_attributes = True