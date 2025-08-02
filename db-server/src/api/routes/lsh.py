"""
LSH configuration endpoints
"""
import uuid
import base64
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...models.lsh import LSHConfig
from ...schemas.lsh import LSHConfigCreate, LSHConfigResponse
from ..deps.auth import verify_api_key

router = APIRouter(prefix="/lsh-configs", tags=["lsh"])


@router.post("", response_model=LSHConfigResponse)
async def create_lsh_config(
    config: LSHConfigCreate,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Create LSH configuration for a client"""
    db_config = LSHConfig(
        client_id=config.client_id,
        num_tables=config.num_tables,
        hash_size=config.hash_size,
        num_candidates=config.num_candidates,
        random_planes=base64.b64decode(config.random_planes)
    )
    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    return db_config


@router.get("/{client_id}", response_model=LSHConfigResponse)
async def get_lsh_config(
    client_id: uuid.UUID,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Get LSH configuration for a client"""
    config = db.query(LSHConfig).filter(LSHConfig.client_id == client_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="LSH config not found")
    return config


@router.delete("/{config_id}")
async def delete_lsh_config(
    config_id: uuid.UUID,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Delete LSH configuration"""
    config = db.query(LSHConfig).filter(LSHConfig.config_id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="LSH config not found")
    
    db.delete(config)
    db.commit()
    return {"message": "LSH config deleted successfully"}