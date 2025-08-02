"""
Embedding management endpoints
"""
import uuid
import base64
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...models.embedding import Embedding, EmbeddingMetadata
from ...schemas.embedding import EmbeddingCreate, EmbeddingUpdate, EmbeddingResponse
from ..deps.auth import verify_api_key

router = APIRouter(prefix="/embeddings", tags=["embeddings"])


@router.post("", response_model=EmbeddingResponse)
async def create_embedding(
    embedding: EmbeddingCreate,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Create a new embedding"""
    db_embedding = Embedding(
        client_id=embedding.client_id,
        external_id=embedding.external_id,
        encrypted_vector=base64.b64decode(embedding.encrypted_vector),
        vector_size_bytes=embedding.vector_size_bytes
    )
    db.add(db_embedding)
    db.commit()
    db.refresh(db_embedding)
    
    # Add metadata if provided
    if embedding.metadata:
        db_metadata = EmbeddingMetadata(
            embedding_id=db_embedding.embedding_id,
            metadata_json=embedding.metadata
        )
        db.add(db_metadata)
        db.commit()
    
    return db_embedding


@router.get("/{embedding_id}", response_model=EmbeddingResponse)
async def get_embedding(
    embedding_id: uuid.UUID,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Get embedding by ID"""
    embedding = db.query(Embedding).filter(Embedding.embedding_id == embedding_id).first()
    if not embedding:
        raise HTTPException(status_code=404, detail="Embedding not found")
    return embedding


@router.get("", response_model=List[EmbeddingResponse])
async def list_embeddings(
    client_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """List embeddings, optionally filtered by client"""
    query = db.query(Embedding)
    if client_id:
        query = query.filter(Embedding.client_id == client_id)
    embeddings = query.offset(skip).limit(limit).all()
    return embeddings


@router.put("/{embedding_id}", response_model=EmbeddingResponse)
async def update_embedding(
    embedding_id: uuid.UUID,
    embedding_update: EmbeddingUpdate,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Update embedding"""
    embedding = db.query(Embedding).filter(Embedding.embedding_id == embedding_id).first()
    if not embedding:
        raise HTTPException(status_code=404, detail="Embedding not found")
    
    for field, value in embedding_update.model_dump(exclude_unset=True).items():
        setattr(embedding, field, value)
    
    db.commit()
    db.refresh(embedding)
    return embedding


@router.delete("/{embedding_id}")
async def delete_embedding(
    embedding_id: uuid.UUID,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Delete embedding (soft delete)"""
    embedding = db.query(Embedding).filter(Embedding.embedding_id == embedding_id).first()
    if not embedding:
        raise HTTPException(status_code=404, detail="Embedding not found")
    
    embedding.is_deleted = True
    from datetime import datetime
    embedding.deleted_at = datetime.utcnow()
    
    db.commit()
    return {"message": "Embedding deleted successfully"}