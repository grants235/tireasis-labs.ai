"""
Pydantic schemas for secure search API endpoints
Based on the secure similarity search architecture
"""
import uuid
from typing import List, Dict, Optional, Any
from pydantic import BaseModel


# ============= INITIALIZATION =============

class InitRequest(BaseModel):
    """Initial handshake to establish HE context"""
    context_params: Dict[str, Any]  # Serialized TenSEAL context parameters
    embedding_dim: int = 384
    lsh_config: Dict[str, int] = {
        "num_tables": 20,
        "hash_size": 16, 
        "num_candidates": 100
    }


class InitResponse(BaseModel):
    """Server confirms initialization"""
    client_id: uuid.UUID  # Generated client ID
    server_id: str
    max_db_size: int
    supported_operations: List[str]
    lsh_config: Dict[str, Any]  # Server's LSH configuration
    random_planes: Optional[str] = None  # Base64 encoded random planes for LSH


# ============= ADD EMBEDDING =============

class AddEmbeddingRequest(BaseModel):
    """Add encrypted embedding to server database"""
    client_id: uuid.UUID
    encrypted_embedding: str  # Base64 encoded encrypted vector
    lsh_hashes: List[int]     # LSH hashes (safe to send in plaintext)
    metadata: Optional[Dict[str, Any]] = None
    embedding_id: Optional[str] = None


class AddEmbeddingResponse(BaseModel):
    """Confirmation of embedding addition"""
    embedding_id: uuid.UUID
    index_position: int
    status: str


# ============= SEARCH =============

class SearchRequest(BaseModel):
    """Search for similar embeddings"""
    client_id: uuid.UUID
    encrypted_query: str      # Base64 encoded encrypted query vector
    lsh_hashes: List[int]     # LSH hashes of query
    top_k: int = 10          # Number of results to return
    rerank_candidates: int = 100  # How many LSH candidates to check with HE


class SearchResult(BaseModel):
    """Individual search result"""
    embedding_id: uuid.UUID
    encrypted_similarity: str  # Base64 encoded encrypted similarity score
    metadata: Optional[Dict[str, Any]] = None


class SearchResponse(BaseModel):
    """Response containing encrypted similarities"""
    results: List[SearchResult]
    candidates_checked: int
    search_time_ms: float


# ============= BATCH OPERATIONS =============

class BatchAddEmbeddingRequest(BaseModel):
    """Add multiple embeddings in batch"""
    client_id: uuid.UUID
    embeddings: List[AddEmbeddingRequest]


class BatchAddEmbeddingResponse(BaseModel):
    """Response for batch embedding addition"""
    batch_id: uuid.UUID
    successful_count: int
    failed_count: int
    embedding_ids: List[uuid.UUID]
    status: str