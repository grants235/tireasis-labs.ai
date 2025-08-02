"""
Pydantic schemas for LSH models
"""
import uuid
from datetime import datetime
from pydantic import BaseModel


class LSHConfigCreate(BaseModel):
    """Schema for creating LSH configuration"""
    client_id: uuid.UUID
    num_tables: int = 20
    hash_size: int = 16
    num_candidates: int = 100
    random_planes: str  # Base64 encoded serialized numpy array


class LSHConfigResponse(BaseModel):
    """Schema for LSH configuration response"""
    config_id: uuid.UUID
    client_id: uuid.UUID
    num_tables: int
    hash_size: int
    num_candidates: int
    created_at: datetime

    class Config:
        from_attributes = True


class LSHHashCreate(BaseModel):
    """Schema for creating LSH hash"""
    client_id: uuid.UUID
    embedding_id: uuid.UUID
    table_index: int
    hash_value: int