"""
LSH hash management endpoints for debugging and maintenance
"""
import uuid
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...models.lsh import LSHHash
from ...schemas.lsh import LSHHashCreate
from ..deps.auth import verify_api_key

router = APIRouter(prefix="/lsh-hashes", tags=["lsh-management"])


@router.post("/batch")
async def add_lsh_hashes_batch(
    lsh_hashes: List[LSHHashCreate],
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Add multiple LSH hashes in batch (for debugging/maintenance)
    """
    try:
        for lsh_hash_data in lsh_hashes:
            db_lsh_hash = LSHHash(
                client_id=lsh_hash_data.client_id,
                embedding_id=lsh_hash_data.embedding_id,
                table_index=lsh_hash_data.table_index,
                hash_value=lsh_hash_data.hash_value
            )
            db.add(db_lsh_hash)
        
        db.commit()
        return {"message": f"Added {len(lsh_hashes)} LSH hashes successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to add LSH hashes: {str(e)}")


@router.get("/client/{client_id}")
async def get_client_lsh_hashes(
    client_id: uuid.UUID,
    table_index: Optional[int] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Get LSH hashes for a specific client, optionally filtered by table index
    """
    query = db.query(LSHHash).filter(LSHHash.client_id == client_id)
    
    if table_index is not None:
        query = query.filter(LSHHash.table_index == table_index)
    
    lsh_hashes = query.limit(limit).all()
    
    return [
        {
            "client_id": lsh_hash.client_id,
            "embedding_id": lsh_hash.embedding_id,
            "table_index": lsh_hash.table_index,
            "hash_value": lsh_hash.hash_value
        }
        for lsh_hash in lsh_hashes
    ]


@router.get("/embedding/{embedding_id}")
async def get_embedding_lsh_hashes(
    embedding_id: uuid.UUID,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Get all LSH hashes for a specific embedding
    """
    lsh_hashes = db.query(LSHHash).filter(LSHHash.embedding_id == embedding_id).all()
    
    if not lsh_hashes:
        raise HTTPException(status_code=404, detail="No LSH hashes found for embedding")
    
    return [
        {
            "client_id": lsh_hash.client_id,
            "embedding_id": lsh_hash.embedding_id,
            "table_index": lsh_hash.table_index,
            "hash_value": lsh_hash.hash_value
        }
        for lsh_hash in lsh_hashes
    ]


@router.delete("/embedding/{embedding_id}")
async def delete_embedding_lsh_hashes(
    embedding_id: uuid.UUID,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Delete all LSH hashes for a specific embedding
    """
    deleted_count = db.query(LSHHash).filter(LSHHash.embedding_id == embedding_id).delete()
    
    if deleted_count == 0:
        raise HTTPException(status_code=404, detail="No LSH hashes found for embedding")
    
    db.commit()
    return {"message": f"Deleted {deleted_count} LSH hashes for embedding {embedding_id}"}


@router.get("/stats/{client_id}")
async def get_lsh_distribution_stats(
    client_id: uuid.UUID,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Get LSH hash distribution statistics for a client
    """
    from sqlalchemy import func
    
    # Get hash distribution per table
    stats = db.query(
        LSHHash.table_index,
        func.count(LSHHash.hash_value.distinct()).label('unique_hashes'),
        func.count(LSHHash.embedding_id).label('total_entries'),
        func.avg(func.count(LSHHash.embedding_id)).over(partition_by=LSHHash.hash_value).label('avg_bucket_size')
    ).filter(
        LSHHash.client_id == client_id
    ).group_by(
        LSHHash.table_index
    ).all()
    
    if not stats:
        raise HTTPException(status_code=404, detail="No LSH statistics found for client")
    
    return [
        {
            "table_index": stat.table_index,
            "unique_hashes": stat.unique_hashes,
            "total_entries": stat.total_entries,
            "avg_bucket_size": float(stat.avg_bucket_size) if stat.avg_bucket_size else 0
        }
        for stat in stats
    ]