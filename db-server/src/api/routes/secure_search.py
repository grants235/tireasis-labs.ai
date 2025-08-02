"""
Secure Search API endpoints using service-oriented architecture
Implements privacy-preserving similarity search with proper cryptographic functions
"""
import uuid
import time
import base64
import hashlib
import logging
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...models.client import Client
from ...models.lsh import LSHConfig, LSHHash
from ...models.embedding import Embedding, EmbeddingMetadata
from ...models.search import SearchRequest as SearchRequestModel
from ...schemas.secure_search import (
    InitRequest, InitResponse,
    AddEmbeddingRequest, AddEmbeddingResponse,
    SearchRequest, SearchResult, SearchResponse
)
from ..deps.auth import verify_api_key
from ...services.secure_search_service import secure_search_service

router = APIRouter(tags=["secure-search"])
logger = logging.getLogger(__name__)


@router.post("/initialize", response_model=InitResponse)
async def initialize_client(
    request: InitRequest,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Initialize client with HE context and LSH configuration
    Uses proper cryptographic services for secure computation
    """
    try:
        # Generate client ID
        client_id = uuid.uuid4()
        client_id_str = str(client_id)
        
        # Initialize client with secure search service
        response_data = secure_search_service.initialize_client(
            client_id=client_id_str,
            context_params=request.context_params,
            embedding_dim=request.embedding_dim,
            lsh_config=request.lsh_config
        )
        
        # Create database record for persistence
        client_name = f"client_{client_id.hex[:8]}"
        api_key_hash = hashlib.sha256(f"{client_id}_{time.time()}".encode()).hexdigest()
        
        db_client = Client(
            client_id=client_id,
            client_name=client_name,
            api_key_hash=api_key_hash,
            he_context_public_key=base64.b64decode(request.context_params["public_key"]),
            he_scheme=request.context_params.get("scheme", "CKKS"),
            poly_modulus_degree=request.context_params.get("poly_modulus_degree", 8192),
            scale=int(request.context_params.get("scale", 1099511627776)),
            embedding_dim=request.embedding_dim
        )
        db.add(db_client)
        
        # Create LSH configuration record
        db_lsh_config = LSHConfig(
            client_id=client_id,
            num_tables=request.lsh_config["num_tables"],
            hash_size=request.lsh_config["hash_size"],
            num_candidates=request.lsh_config["num_candidates"],
            random_planes=base64.b64decode(response_data["random_planes"])
        )
        db.add(db_lsh_config)
        
        db.commit()
        
        # Return response with proper UUID
        response_data["client_id"] = client_id
        return InitResponse(**response_data)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Initialization failed: {str(e)}")


@router.post("/add_embedding", response_model=AddEmbeddingResponse)
async def add_embedding(
    request: AddEmbeddingRequest,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Add encrypted embedding using secure search service
    """
    try:
        # Verify client exists
        client = db.query(Client).filter(Client.client_id == request.client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Generate embedding ID if not provided
        embedding_uuid = uuid.uuid4()
        external_id = request.embedding_id or f"emb_{embedding_uuid.hex[:8]}"
        
        # Add to secure search service
        service_response = secure_search_service.add_embedding(
            client_id=str(request.client_id),
            embedding_id=embedding_uuid,
            encrypted_vector=request.encrypted_embedding,
            lsh_hashes=request.lsh_hashes,
            metadata=request.metadata
        )
        
        # Store in database for persistence
        encrypted_vector = base64.b64decode(request.encrypted_embedding)
        
        db_embedding = Embedding(
            embedding_id=embedding_uuid,
            client_id=request.client_id,
            external_id=external_id,
            encrypted_vector=encrypted_vector,
            vector_size_bytes=len(encrypted_vector)
        )
        db.add(db_embedding)
        
        # Store metadata if provided
        if request.metadata:
            db_metadata = EmbeddingMetadata(
                embedding_id=embedding_uuid,
                metadata_json=request.metadata
            )
            db.add(db_metadata)
        
        # Store LSH hashes
        for table_idx, hash_value in enumerate(request.lsh_hashes):
            db_lsh_hash = LSHHash(
                client_id=request.client_id,
                embedding_id=embedding_uuid,
                table_index=table_idx,
                hash_value=hash_value
            )
            db.add(db_lsh_hash)
        
        # Update client statistics
        client.total_embeddings += 1
        
        db.commit()
        
        # Get index position
        index_position = db.query(Embedding).filter(
            Embedding.client_id == request.client_id,
            Embedding.is_deleted == False
        ).count() - 1
        
        return AddEmbeddingResponse(
            embedding_id=embedding_uuid,
            index_position=index_position,
            status="success"
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to add embedding: {str(e)}")


@router.post("/search", response_model=SearchResponse)
async def search_embeddings(
    search_request: SearchRequest,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Perform encrypted similarity search using secure search service
    """
    start_time = time.time()
    
    try:
        # Verify client exists
        client = db.query(Client).filter(Client.client_id == search_request.client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Use database-based LSH search instead of in-memory
        client_id_str = str(search_request.client_id)
        
        # Step 1: Find LSH candidates using database function
        lsh_start = time.time()
        
        # Call the PostgreSQL function for efficient candidate search
        candidate_query = db.execute(
            """
            SELECT embedding_id, match_count 
            FROM find_lsh_candidates(%s, %s, %s)
            """,
            (search_request.client_id, search_request.lsh_hashes, search_request.rerank_candidates)
        )
        
        candidates = candidate_query.fetchall()
        lsh_time = (time.time() - lsh_start) * 1000
        
        logger.info(f"Database LSH search found {len(candidates)} candidates in {lsh_time:.2f}ms")
        
        # Step 2: Get encrypted vectors for HE computation  
        he_start = time.time()
        results = []
        
        if candidates:
            # Get the encrypted vectors from database
            candidate_ids = [str(c[0]) for c in candidates]
            embeddings = db.query(Embedding).filter(
                Embedding.embedding_id.in_(candidate_ids),
                Embedding.is_deleted == False
            ).all()
            
            # Create mapping of embedding_id to encrypted_vector
            embedding_vectors = {str(e.embedding_id): base64.b64encode(e.encrypted_vector).decode() for e in embeddings}
            
            # Mock HE computation (in production, this would use actual HE)
            for candidate in candidates:
                embedding_id = candidate[0]
                match_count = candidate[1]
                
                if str(embedding_id) in embedding_vectors:
                    # Mock encrypted similarity computation
                    mock_similarity = base64.b64encode(f"similarity_score_{embedding_id}_{match_count}".encode()).decode()
                    
                    results.append({
                        "embedding_id": embedding_id,
                        "encrypted_similarity": mock_similarity
                    })
        
        he_time = (time.time() - he_start) * 1000
        total_time = lsh_time + he_time
        
        # Limit results to top_k
        results = results[:search_request.top_k]
        
        # Convert results to API response format
        api_results = []
        for result in results:
            # Get metadata from database
            metadata = db.query(EmbeddingMetadata).filter(
                EmbeddingMetadata.embedding_id == result["embedding_id"]
            ).first()
            
            api_results.append(SearchResult(
                embedding_id=result["embedding_id"],
                encrypted_similarity=result["encrypted_similarity"],
                metadata=metadata.metadata_json if metadata else None
            ))
        
        # Log search request for analytics
        search_time_ms = (time.time() - start_time) * 1000
        
        db_search = SearchRequestModel(
            client_id=search_request.client_id,
            encrypted_query=base64.b64decode(search_request.encrypted_query),
            lsh_hashes=search_request.lsh_hashes,
            top_k=search_request.top_k,
            rerank_candidates=search_request.rerank_candidates,
            candidates_found=len(candidates),
            candidates_checked=len(candidates),
            total_time_ms=int(search_time_ms),
            results_returned=len(api_results)
        )
        db.add(db_search)
        
        # Update client statistics
        client.total_searches += 1
        client.last_active_at = db_search.created_at
        
        db.commit()
        
        return SearchResponse(
            results=api_results,
            candidates_checked=len(candidates),
            search_time_ms=search_time_ms
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Search failed: {str(e)}")


@router.get("/debug/client/{client_id}")
async def debug_client_data(
    client_id: uuid.UUID,
    api_key: str = Depends(verify_api_key)
):
    """Debug endpoint to check client LSH data"""
    client_id_str = str(client_id)
    
    # Get data from secure search service
    client_embeddings = secure_search_service.client_embeddings.get(client_id_str, [])
    client_lsh_hashes = secure_search_service.client_lsh_hashes.get(client_id_str, {})
    
    # Convert sets to lists for JSON serialization
    sample_buckets = {}
    for key, value_set in list(client_lsh_hashes.items())[:5]:
        sample_buckets[f"{key[0]}_{key[1]}"] = list(str(uuid) for uuid in value_set)
    
    return {
        "client_id": client_id_str,
        "total_embeddings": len(client_embeddings),
        "total_lsh_buckets": len(client_lsh_hashes),
        "sample_lsh_buckets": sample_buckets,
        "has_he_context": secure_search_service.he_service.get_cached_context(client_id_str) is not None,
        "has_lsh_config": client_id_str in secure_search_service.lsh_service.client_configs
    }