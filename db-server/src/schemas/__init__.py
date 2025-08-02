"""
Pydantic schemas for API request/response models
"""
from .client import ClientCreate, ClientUpdate, ClientResponse
from .lsh import LSHConfigCreate, LSHConfigResponse, LSHHashCreate
from .embedding import (
    EmbeddingCreate, 
    EmbeddingUpdate, 
    EmbeddingResponse,
    EmbeddingMetadataCreate,
    EmbeddingMetadataResponse
)
from .search import SearchRequestCreate, SearchRequestUpdate, SearchRequestResponse
from .secure_search import (
    InitRequest, InitResponse,
    AddEmbeddingRequest, AddEmbeddingResponse,
    SearchRequest, SearchResult, SearchResponse,
    BatchAddEmbeddingRequest, BatchAddEmbeddingResponse
)

__all__ = [
    # Client schemas
    "ClientCreate",
    "ClientUpdate", 
    "ClientResponse",
    # LSH schemas
    "LSHConfigCreate",
    "LSHConfigResponse",
    "LSHHashCreate",
    # Embedding schemas
    "EmbeddingCreate",
    "EmbeddingUpdate",
    "EmbeddingResponse", 
    "EmbeddingMetadataCreate",
    "EmbeddingMetadataResponse",
    # Search schemas
    "SearchRequestCreate",
    "SearchRequestUpdate",
    "SearchRequestResponse",
    # Secure search schemas
    "InitRequest",
    "InitResponse",
    "AddEmbeddingRequest", 
    "AddEmbeddingResponse",
    "SearchRequest",
    "SearchResult",
    "SearchResponse",
    "BatchAddEmbeddingRequest",
    "BatchAddEmbeddingResponse"
]