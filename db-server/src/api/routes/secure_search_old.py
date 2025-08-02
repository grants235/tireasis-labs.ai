"""
Secure Search API endpoints implementing the privacy-preserving similarity search
"""
import uuid
import time
import base64
import hashlib
from typing import List, Set
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


@router.post("/initialize", response_model=InitResponse)
async def initialize_client(
    request: InitRequest,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Initialize client with HE context and LSH configuration
    This establishes the secure connection between client and server
    """
    try:
        # Generate client ID
        client_id = uuid.uuid4()
        
        # Create client record with HE context
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
        db.commit()
        db.refresh(db_client)
        
        # Create LSH configuration
        # Generate actual random planes for LSH hashing
        print(f"[DEBUG] Generating random planes for client {client_id}")
        import numpy as np
        import pickle
        
        num_tables = request.lsh_config["num_tables"]
        hash_size = request.lsh_config["hash_size"]
        embedding_dim = request.embedding_dim
        
        print(f"[DEBUG] LSH config: tables={num_tables}, hash_size={hash_size}, dim={embedding_dim}")
        
        # Generate random hyperplanes for LSH
        np.random.seed(int(client_id.hex[:8], 16))  # Deterministic seed based on client ID
        random_planes = np.random.randn(num_tables, hash_size, embedding_dim)
        
        print(f"[DEBUG] Generated random planes shape: {random_planes.shape}")
        
        # Serialize the random planes
        random_planes_data = pickle.dumps(random_planes)
        random_planes_b64 = base64.b64encode(random_planes_data).decode('utf-8')
        
        print(f"[DEBUG] Serialized random planes length: {len(random_planes_b64)}")
        
        db_lsh_config = LSHConfig(
            client_id=client_id,
            num_tables=request.lsh_config["num_tables"],
            hash_size=request.lsh_config["hash_size"],
            num_candidates=request.lsh_config["num_candidates"],
            random_planes=random_planes_data
        )
        db.add(db_lsh_config)
        db.commit()
        
        return InitResponse(
            client_id=client_id,
            server_id="secure-search-server-001",
            max_db_size=100000,
            supported_operations=["add_embedding", "search", "batch_search"],
            lsh_config={
                "num_tables": db_lsh_config.num_tables,
                "hash_size": db_lsh_config.hash_size,
                "num_candidates": db_lsh_config.num_candidates
            },
            random_planes=random_planes_b64
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Initialization failed: {str(e)}")


@router.post("/add_embedding", response_model=AddEmbeddingResponse)
async def add_embedding(
    request: AddEmbeddingRequest,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Add encrypted embedding with LSH hashes to the database
    """
    try:
        # Verify client exists
        client = db.query(Client).filter(Client.client_id == request.client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Generate embedding ID if not provided
        embedding_uuid = uuid.uuid4()
        external_id = request.embedding_id or f"emb_{embedding_uuid.hex[:8]}"
        
        # Decode and store encrypted embedding
        encrypted_vector = base64.b64decode(request.encrypted_embedding)
        
        # Create embedding record
        db_embedding = Embedding(
            embedding_id=embedding_uuid,
            client_id=request.client_id,
            external_id=external_id,
            encrypted_vector=encrypted_vector,
            vector_size_bytes=len(encrypted_vector)
        )
        db.add(db_embedding)
        db.commit()
        db.refresh(db_embedding)
        
        # Store metadata if provided
        if request.metadata:
            db_metadata = EmbeddingMetadata(
                embedding_id=embedding_uuid,
                metadata_json=request.metadata
            )
            db.add(db_metadata)
            db.commit()
        
        # Store LSH hashes for fast similarity search
        for table_idx, hash_value in enumerate(request.lsh_hashes):
            db_lsh_hash = LSHHash(
                client_id=request.client_id,
                embedding_id=embedding_uuid,
                table_index=table_idx,
                hash_value=hash_value
            )
            db.add(db_lsh_hash)
        
        db.commit()
        
        # Update client statistics
        client.total_embeddings += 1
        db.commit()
        
        # Get index position (number of embeddings for this client)
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
    Perform encrypted similarity search using LSH + Homomorphic Encryption
    """
    start_time = time.time()
    
    try:
        # Verify client exists
        client = db.query(Client).filter(Client.client_id == search_request.client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Get LSH configuration
        lsh_config = db.query(LSHConfig).filter(LSHConfig.client_id == search_request.client_id).first()
        if not lsh_config:
            raise HTTPException(status_code=404, detail="LSH configuration not found")
        
        # Step 1: Find LSH candidates
        candidates: Set[uuid.UUID] = set()
        
        # Query LSH hash tables to find matching embeddings
        print(f"[DEBUG] Search request LSH hashes: {search_request.lsh_hashes}")
        for table_idx, hash_value in enumerate(search_request.lsh_hashes):
            if table_idx >= lsh_config.num_tables:
                break
                
            print(f"[DEBUG] Looking for table {table_idx}, hash {hash_value}")
            
            # Find embeddings with matching hash in this table
            matching_hashes = db.query(LSHHash).filter(
                LSHHash.client_id == search_request.client_id,
                LSHHash.table_index == table_idx,
                LSHHash.hash_value == hash_value
            ).all()
            
            for lsh_hash in matching_hashes:
                candidates.add(lsh_hash.embedding_id)
        
        # Limit candidates based on configuration
        candidate_list = list(candidates)[:search_request.rerank_candidates]
        
        # Step 2: Get candidate embeddings with metadata
        results = []
        
        for embedding_id in candidate_list:
            # Get embedding
            embedding = db.query(Embedding).filter(
                Embedding.embedding_id == embedding_id,
                Embedding.client_id == search_request.client_id,
                Embedding.is_deleted == False
            ).first()
            
            if not embedding:
                continue
            
            # Get metadata
            metadata = db.query(EmbeddingMetadata).filter(
                EmbeddingMetadata.embedding_id == embedding_id
            ).first()
            
            # In a real implementation, this is where we would:
            # 1. Deserialize the encrypted query and embedding vectors
            # 2. Compute encrypted dot product using homomorphic encryption
            # 3. Return the encrypted similarity score
            
            # For this MVP, we create a placeholder encrypted similarity
            # The actual HE computation would happen here
            encrypted_similarity = base64.b64encode(
                f"encrypted_sim_{embedding_id}".encode()
            ).decode('utf-8')
            
            results.append(SearchResult(
                embedding_id=embedding_id,
                encrypted_similarity=encrypted_similarity,
                metadata=metadata.metadata_json if metadata else None
            ))
        
        # Limit results to top_k
        # Note: Server cannot sort by similarity since scores are encrypted
        # Client will decrypt and sort on their side
        results = results[:search_request.top_k * 2]  # Return extra for client to sort
        
        # Step 3: Log search request for analytics
        search_time_ms = (time.time() - start_time) * 1000
        
        db_search = SearchRequestModel(
            client_id=search_request.client_id,
            encrypted_query=base64.b64decode(search_request.encrypted_query),
            lsh_hashes=search_request.lsh_hashes,
            top_k=search_request.top_k,
            rerank_candidates=search_request.rerank_candidates,
            candidates_found=len(candidates),
            candidates_checked=len(candidate_list),
            total_time_ms=int(search_time_ms),
            results_returned=len(results)
        )
        db.add(db_search)
        
        # Update client statistics
        client.total_searches += 1
        db.commit()
        
        return SearchResponse(
            results=results,
            candidates_checked=len(candidate_list),
            search_time_ms=search_time_ms
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/client/{client_id}/stats")
async def get_client_stats(
    client_id: uuid.UUID,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Get client statistics and usage information
    """
    client = db.query(Client).filter(Client.client_id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Get embedding count
    embedding_count = db.query(Embedding).filter(
        Embedding.client_id == client_id,
        Embedding.is_deleted == False
    ).count()
    
    # Get recent search count
    search_count = db.query(SearchRequestModel).filter(
        SearchRequestModel.client_id == client_id
    ).count()
    
    return {
        "client_id": client_id,
        "client_name": client.client_name,
        "total_embeddings": embedding_count,
        "total_searches": search_count,
        "embedding_dim": client.embedding_dim,
        "max_embeddings_allowed": client.max_embeddings_allowed,
        "last_active_at": client.last_active_at,
        "is_active": client.is_active
    }