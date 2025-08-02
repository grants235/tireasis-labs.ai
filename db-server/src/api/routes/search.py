"""
Search request endpoints
"""
import uuid
import base64
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...models.search import SearchRequest
from ...schemas.search import SearchRequestCreate, SearchRequestUpdate, SearchRequestResponse
from ..deps.auth import verify_api_key

router = APIRouter(prefix="/search-requests", tags=["search"])


@router.post("", response_model=SearchRequestResponse)
async def create_search_request(
    search: SearchRequestCreate,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Create a new search request"""
    db_search = SearchRequest(
        client_id=search.client_id,
        encrypted_query=base64.b64decode(search.encrypted_query),
        lsh_hashes=search.lsh_hashes,
        top_k=search.top_k,
        rerank_candidates=search.rerank_candidates
    )
    db.add(db_search)
    db.commit()
    db.refresh(db_search)
    return db_search


@router.get("/{search_id}", response_model=SearchRequestResponse)
async def get_search_request(
    search_id: uuid.UUID,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Get search request by ID"""
    search = db.query(SearchRequest).filter(SearchRequest.search_id == search_id).first()
    if not search:
        raise HTTPException(status_code=404, detail="Search request not found")
    return search


@router.get("", response_model=List[SearchRequestResponse])
async def list_search_requests(
    client_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """List search requests, optionally filtered by client"""
    query = db.query(SearchRequest)
    if client_id:
        query = query.filter(SearchRequest.client_id == client_id)
    searches = query.offset(skip).limit(limit).all()
    return searches


@router.put("/{search_id}", response_model=SearchRequestResponse)
async def update_search_request(
    search_id: uuid.UUID,
    search_update: SearchRequestUpdate,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Update search request with performance metrics"""
    search = db.query(SearchRequest).filter(SearchRequest.search_id == search_id).first()
    if not search:
        raise HTTPException(status_code=404, detail="Search request not found")
    
    for field, value in search_update.model_dump(exclude_unset=True).items():
        setattr(search, field, value)
    
    db.commit()
    db.refresh(search)
    return search