"""
Secure Search Service
Orchestrates homomorphic encryption and LSH for privacy-preserving similarity search
"""
import uuid
import time
import base64
import numpy as np
from typing import List, Dict, Set, Tuple, Optional, Any
from dataclasses import dataclass
import logging

from .homomorphic_encryption import he_service as global_he_service, HomomorphicEncryptionService
from .lsh_search import lsh_service as global_lsh_service, LSHSearchService, LSHConfig

logger = logging.getLogger(__name__)


@dataclass 
class SearchResult:
    """Result from secure similarity search"""
    embedding_id: uuid.UUID
    encrypted_similarity: str
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class SearchStats:
    """Statistics from a search operation"""
    total_embeddings: int
    candidates_found: int
    candidates_checked: int
    search_time_ms: float
    lsh_time_ms: float
    he_time_ms: float


class SecureSearchService:
    """
    Main service for secure similarity search
    Combines LSH for candidate selection with HE for secure similarity computation
    """
    
    def __init__(self, 
                 he_service: HomomorphicEncryptionService = None,
                 lsh_service: LSHSearchService = None):
        self.he_service = he_service or global_he_service
        self.lsh_service = lsh_service or global_lsh_service
        
        # Client data storage
        self.client_contexts: Dict[str, Any] = {}
        self.client_embeddings: Dict[str, List[Tuple[uuid.UUID, str]]] = {}  # client_id -> [(embedding_id, encrypted_vector)]
        self.client_lsh_hashes: Dict[str, Dict[Tuple[int, int], Set[uuid.UUID]]] = {}  # client_id -> {(table, hash): {embedding_ids}}
        
    def initialize_client(self,
                         client_id: str,
                         context_params: Dict[str, Any],
                         embedding_dim: int = 384,
                         lsh_config: Dict[str, int] = None) -> Dict[str, Any]:
        """
        Initialize a new client with HE context and LSH configuration
        
        Args:
            client_id: Unique client identifier
            context_params: HE context parameters
            embedding_dim: Dimension of embedding vectors
            lsh_config: LSH configuration parameters
            
        Returns:
            Initialization response with random planes for LSH
        """
        start_time = time.time()
        
        # Set default LSH config
        if lsh_config is None:
            lsh_config = {
                "num_tables": 20,
                "hash_size": 16,
                "num_candidates": 100
            }
        
        try:
            # Create HE context
            he_context = self.he_service.create_context(
                poly_modulus_degree=context_params.get("poly_modulus_degree", 8192),
                scale=context_params.get("scale", 2**40)
            )
            
            # Cache the context
            self.he_service.cache_context(client_id, he_context)
            
            # Create LSH configuration
            lsh_config_obj = self.lsh_service.create_lsh_config(
                client_id=client_id,
                num_tables=lsh_config["num_tables"],
                hash_size=lsh_config["hash_size"],
                embedding_dim=embedding_dim
            )
            
            # Generate and cache random planes
            random_planes = self.lsh_service.generate_random_planes(lsh_config_obj)
            self.lsh_service.cache_random_planes(client_id, random_planes)
            
            # Initialize client data structures
            self.client_embeddings[client_id] = []
            self.client_lsh_hashes[client_id] = {}
            
            # Serialize random planes for client
            random_planes_b64 = self.lsh_service.serialize_random_planes(random_planes)
            
            init_time = (time.time() - start_time) * 1000
            logger.info(f"Initialized client {client_id} in {init_time:.2f}ms")
            
            return {
                "client_id": client_id,
                "server_id": "secure-search-server-001",
                "max_db_size": 100000,
                "supported_operations": ["add_embedding", "search", "batch_search"],
                "lsh_config": {
                    "num_tables": lsh_config_obj.num_tables,
                    "hash_size": lsh_config_obj.hash_size,
                    "embedding_dim": lsh_config_obj.embedding_dim
                },
                "random_planes": random_planes_b64,
                "initialization_time_ms": init_time
            }
            
        except Exception as e:
            logger.error(f"Failed to initialize client {client_id}: {e}")
            raise
    
    def add_embedding(self,
                     client_id: str,
                     embedding_id: uuid.UUID,
                     encrypted_vector: str,
                     lsh_hashes: List[int],
                     metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Add an encrypted embedding to the client's database
        
        Args:
            client_id: Client identifier
            embedding_id: Unique embedding identifier
            encrypted_vector: Base64 encoded encrypted vector
            lsh_hashes: LSH hash values for the vector
            metadata: Optional metadata for the embedding
            
        Returns:
            Add embedding response
        """
        start_time = time.time()
        
        try:
            # Validate client exists
            if client_id not in self.client_embeddings:
                raise ValueError(f"Client {client_id} not initialized")
            
            # Store encrypted embedding
            self.client_embeddings[client_id].append((embedding_id, encrypted_vector))
            
            # Store LSH hashes
            client_lsh_data = self.client_lsh_hashes[client_id]
            
            logger.info(f"Adding embedding {embedding_id} with LSH hashes: {lsh_hashes}")
            
            for table_idx, hash_value in enumerate(lsh_hashes):
                key = (table_idx, hash_value)
                if key not in client_lsh_data:
                    client_lsh_data[key] = set()
                client_lsh_data[key].add(embedding_id)
            
            logger.info(f"Total LSH buckets after add: {len(client_lsh_data)}")
            
            add_time = (time.time() - start_time) * 1000
            
            logger.info(f"Added embedding {embedding_id} for client {client_id} "
                       f"in {add_time:.2f}ms")
            
            return {
                "embedding_id": embedding_id,
                "status": "success",
                "add_time_ms": add_time,
                "total_embeddings": len(self.client_embeddings[client_id])
            }
            
        except Exception as e:
            logger.error(f"Failed to add embedding for client {client_id}: {e}")
            raise
    
    def search_embeddings(self,
                         client_id: str,
                         encrypted_query: str,
                         lsh_hashes: List[int],
                         top_k: int = 10,
                         rerank_candidates: int = 100) -> Tuple[List[SearchResult], SearchStats]:
        """
        Perform secure similarity search
        
        Args:
            client_id: Client identifier
            encrypted_query: Base64 encoded encrypted query vector
            lsh_hashes: LSH hashes of query vector
            top_k: Number of results to return
            rerank_candidates: Maximum candidates to check with HE
            
        Returns:
            Tuple of (search results, search statistics)
        """
        start_time = time.time()
        
        try:
            # Validate client exists
            if client_id not in self.client_embeddings:
                raise ValueError(f"Client {client_id} not initialized")
            
            client_embeddings = self.client_embeddings[client_id]
            total_embeddings = len(client_embeddings)
            
            if total_embeddings == 0:
                return [], SearchStats(
                    total_embeddings=0,
                    candidates_found=0,
                    candidates_checked=0,
                    search_time_ms=0,
                    lsh_time_ms=0,
                    he_time_ms=0
                )
            
            # Step 1: LSH candidate selection
            lsh_start = time.time()
            
            # Debug logging
            stored_hashes = self.client_lsh_hashes[client_id]
            logger.info(f"Search debug for client {client_id}:")
            logger.info(f"  Query hashes: {lsh_hashes}")
            logger.info(f"  Stored hash buckets: {len(stored_hashes)}")
            logger.info(f"  Total embeddings: {total_embeddings}")
            
            candidates = self.lsh_service.find_candidate_embeddings(
                client_id=client_id,
                query_hashes=lsh_hashes,
                stored_hashes=stored_hashes,
                min_matches=1  # At least 1 table match required
            )
            
            lsh_time = (time.time() - lsh_start) * 1000
            
            # Limit candidates for HE computation
            candidate_list = list(candidates)[:rerank_candidates]
            
            # Step 2: Homomorphic encryption similarity computation
            he_start = time.time()
            
            results = []
            he_context = self.he_service.get_cached_context(client_id)
            
            if he_context is None:
                raise ValueError(f"No cached HE context for client {client_id}")
            
            for embedding_id in candidate_list:
                # Find the encrypted vector for this embedding
                encrypted_vector = None
                for stored_id, stored_vector in client_embeddings:
                    if stored_id == embedding_id:
                        encrypted_vector = stored_vector
                        break
                
                if encrypted_vector is None:
                    continue
                
                # Compute encrypted similarity
                try:
                    encrypted_similarity = self.he_service.compute_encrypted_similarity(
                        context=he_context,
                        encrypted_query=encrypted_query,
                        encrypted_vector=encrypted_vector
                    )
                    
                    results.append(SearchResult(
                        embedding_id=embedding_id,
                        encrypted_similarity=encrypted_similarity,
                        metadata=None  # Would be retrieved from database in full implementation
                    ))
                    
                except Exception as e:
                    logger.warning(f"Failed to compute similarity for {embedding_id}: {e}")
                    continue
            
            he_time = (time.time() - he_start) * 1000
            
            # Limit results to top_k
            # Note: Server cannot sort by similarity since scores are encrypted
            # Client will decrypt and sort on their side
            results = results[:top_k * 2]  # Return extra for client to sort
            
            total_time = (time.time() - start_time) * 1000
            
            stats = SearchStats(
                total_embeddings=total_embeddings,
                candidates_found=len(candidates),
                candidates_checked=len(candidate_list),
                search_time_ms=total_time,
                lsh_time_ms=lsh_time,
                he_time_ms=he_time
            )
            
            logger.info(f"Search completed for client {client_id}: "
                       f"{len(results)} results from {len(candidates)} candidates "
                       f"in {total_time:.2f}ms")
            
            return results, stats
            
        except Exception as e:
            logger.error(f"Search failed for client {client_id}: {e}")
            raise
    
    def get_client_stats(self, client_id: str) -> Dict[str, Any]:
        """Get statistics for a client"""
        if client_id not in self.client_embeddings:
            raise ValueError(f"Client {client_id} not found")
        
        return {
            "client_id": client_id,
            "total_embeddings": len(self.client_embeddings[client_id]),
            "lsh_buckets": len(self.client_lsh_hashes[client_id]),
            "has_he_context": self.he_service.get_cached_context(client_id) is not None,
            "has_lsh_config": client_id in self.lsh_service.client_configs
        }
    
    def load_client_data_from_db(self, client_id: str, db_session):
        """Load client data from database into memory"""
        from ..models.embedding import Embedding
        from ..models.lsh import LSHHash
        from ..models.client import Client
        import uuid as uuid_module
        
        # Convert string to UUID for database query
        client_uuid = uuid_module.UUID(client_id)
        
        # Initialize client data structures if not exists
        if client_id not in self.client_embeddings:
            self.client_embeddings[client_id] = []
        if client_id not in self.client_lsh_hashes:
            self.client_lsh_hashes[client_id] = {}
        
        # Load embeddings
        embeddings = db_session.query(Embedding).filter(
            Embedding.client_id == client_uuid,
            Embedding.is_deleted == False
        ).all()
        
        # Clear existing in-memory data
        self.client_embeddings[client_id] = []
        self.client_lsh_hashes[client_id] = {}
        
        # Load embeddings into memory
        for embedding in embeddings:
            # Convert encrypted vector back to base64 string
            encrypted_vector_b64 = base64.b64encode(embedding.encrypted_vector).decode()
            self.client_embeddings[client_id].append((embedding.embedding_id, encrypted_vector_b64))
        
        # Load LSH hashes
        lsh_hashes = db_session.query(LSHHash).filter(
            LSHHash.client_id == client_uuid
        ).all()
        
        client_lsh_data = self.client_lsh_hashes[client_id]
        for lsh_hash in lsh_hashes:
            key = (lsh_hash.table_index, lsh_hash.hash_value)
            if key not in client_lsh_data:
                client_lsh_data[key] = set()
            client_lsh_data[key].add(lsh_hash.embedding_id)
        
        logger.info(f"Loaded {len(embeddings)} embeddings and {len(lsh_hashes)} LSH hashes for client {client_id}")
        return len(embeddings), len(lsh_hashes)
    
    def clear_client_data(self, client_id: str):
        """Clear all data for a client"""
        self.client_embeddings.pop(client_id, None)
        self.client_lsh_hashes.pop(client_id, None)
        self.he_service.clear_context_cache(client_id)
        self.lsh_service.clear_client_data(client_id)
        logger.info(f"Cleared all data for client {client_id}")


# Global service instance
secure_search_service = SecureSearchService()