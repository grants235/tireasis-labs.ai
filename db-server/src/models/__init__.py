"""
Database models for secure search system
"""
from .client import Client
from .lsh import LSHConfig, LSHHash
from .embedding import Embedding, EmbeddingMetadata
from .search import SearchRequest

# Import all models to ensure they're registered with SQLAlchemy
__all__ = [
    "Client",
    "LSHConfig", 
    "LSHHash",
    "Embedding",
    "EmbeddingMetadata", 
    "SearchRequest"
]