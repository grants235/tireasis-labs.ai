"""
Client management endpoints
"""
import uuid
import base64
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...models.client import Client
from ...schemas.client import ClientCreate, ClientUpdate, ClientResponse
from ..deps.auth import verify_api_key

router = APIRouter(prefix="/clients", tags=["clients"])


@router.post("", response_model=ClientResponse)
async def create_client(
    client: ClientCreate,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Create a new client"""
    db_client = Client(
        client_name=client.client_name,
        api_key_hash=client.api_key_hash,
        he_context_public_key=base64.b64decode(client.he_context_public_key),
        he_scheme=client.he_scheme,
        poly_modulus_degree=client.poly_modulus_degree,
        scale=client.scale,
        embedding_dim=client.embedding_dim,
        max_embeddings_allowed=client.max_embeddings_allowed
    )
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    return db_client


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: uuid.UUID,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Get client by ID"""
    client = db.query(Client).filter(Client.client_id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.get("", response_model=List[ClientResponse])
async def list_clients(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """List all clients"""
    clients = db.query(Client).offset(skip).limit(limit).all()
    return clients


@router.put("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: uuid.UUID,
    client_update: ClientUpdate,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Update client"""
    client = db.query(Client).filter(Client.client_id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    for field, value in client_update.model_dump(exclude_unset=True).items():
        setattr(client, field, value)
    
    db.commit()
    db.refresh(client)
    return client


@router.get("/{client_id}/stats")
async def get_client_stats(
    client_id: uuid.UUID,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Get client statistics"""
    client = db.query(Client).filter(Client.client_id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    return {
        "client_id": str(client.client_id),
        "client_name": client.client_name,
        "total_embeddings": client.total_embeddings,
        "total_searches": client.total_searches,
        "embedding_dim": client.embedding_dim,
        "max_embeddings_allowed": client.max_embeddings_allowed,
        "last_active_at": client.last_active_at.isoformat() if client.last_active_at else None,
        "is_active": client.is_active,
        "created_at": client.created_at.isoformat(),
        "updated_at": client.updated_at.isoformat()
    }


@router.delete("/{client_id}")
async def delete_client(
    client_id: uuid.UUID,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Delete client"""
    client = db.query(Client).filter(Client.client_id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    db.delete(client)
    db.commit()
    return {"message": "Client deleted successfully"}