"""
Locality-Sensitive Hashing (LSH) Service
Provides efficient approximate similarity search for high-dimensional vectors
"""
import numpy as np
import pickle
import base64
import hashlib
from typing import List, Tuple, Set, Dict, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class LSHConfig:
    """Configuration for LSH algorithm"""
    num_tables: int = 20          # Number of hash tables
    hash_size: int = 16           # Number of bits per hash
    embedding_dim: int = 384      # Dimension of input vectors
    random_seed: int = 42         # Seed for reproducible random planes


class LSHSearchService:
    """
    Locality-Sensitive Hashing service for efficient similarity search
    Uses random hyperplanes to create hash functions for cosine similarity
    """
    
    def __init__(self):
        self.client_configs: Dict[str, LSHConfig] = {}
        self.random_planes_cache: Dict[str, np.ndarray] = {}
    
    def create_lsh_config(self, 
                         client_id: str,
                         num_tables: int = 20,
                         hash_size: int = 16,
                         embedding_dim: int = 384,
                         random_seed: Optional[int] = None) -> LSHConfig:
        """
        Create LSH configuration for a client
        
        Args:
            client_id: Unique client identifier
            num_tables: Number of hash tables (higher = better recall, slower)
            hash_size: Bits per hash (higher = more precision, less recall)
            embedding_dim: Dimension of input vectors
            random_seed: Seed for random planes (None = deterministic from client_id)
            
        Returns:
            LSH configuration object
        """
        if random_seed is None:
            # Create deterministic seed from client ID
            random_seed = int(hashlib.md5(client_id.encode()).hexdigest()[:8], 16)
        
        config = LSHConfig(
            num_tables=num_tables,
            hash_size=hash_size,
            embedding_dim=embedding_dim,
            random_seed=random_seed
        )
        
        self.client_configs[client_id] = config
        logger.info(f"Created LSH config for client {client_id}: "
                   f"{num_tables} tables, {hash_size} bits, {embedding_dim}D")
        
        return config
    
    def generate_random_planes(self, config: LSHConfig) -> np.ndarray:
        """
        Generate random hyperplanes for LSH hashing
        
        Args:
            config: LSH configuration
            
        Returns:
            Random planes array of shape (num_tables, hash_size, embedding_dim)
        """
        np.random.seed(config.random_seed)
        
        # Generate random hyperplanes
        # Each plane is a unit vector in embedding_dim space
        random_planes = np.random.randn(
            config.num_tables, 
            config.hash_size, 
            config.embedding_dim
        )
        
        # Normalize each hyperplane to unit length
        for table_idx in range(config.num_tables):
            for bit_idx in range(config.hash_size):
                plane = random_planes[table_idx, bit_idx]
                norm = np.linalg.norm(plane)
                if norm > 0:
                    random_planes[table_idx, bit_idx] = plane / norm
        
        logger.info(f"Generated random planes: {random_planes.shape}")
        return random_planes
    
    def cache_random_planes(self, client_id: str, random_planes: np.ndarray):
        """Cache random planes for a client"""
        self.random_planes_cache[client_id] = random_planes
        logger.info(f"Cached random planes for client {client_id}")
    
    def get_random_planes(self, client_id: str) -> Optional[np.ndarray]:
        """Get cached random planes for a client"""
        return self.random_planes_cache.get(client_id)
    
    def serialize_random_planes(self, random_planes: np.ndarray) -> str:
        """Serialize random planes to base64 string"""
        planes_bytes = pickle.dumps(random_planes)
        return base64.b64encode(planes_bytes).decode('utf-8')
    
    def deserialize_random_planes(self, planes_b64: str) -> np.ndarray:
        """Deserialize random planes from base64 string"""
        planes_bytes = base64.b64decode(planes_b64.encode('utf-8'))
        return pickle.loads(planes_bytes)
    
    def compute_lsh_hashes(self, 
                          client_id: str, 
                          vector: np.ndarray) -> List[int]:
        """
        Compute LSH hashes for a vector using client's random planes
        
        Args:
            client_id: Client identifier
            vector: Input vector to hash
            
        Returns:
            List of LSH hash values (one per table)
        """
        # Get cached random planes
        random_planes = self.get_random_planes(client_id)
        if random_planes is None:
            raise ValueError(f"No random planes found for client {client_id}")
        
        # Normalize input vector
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        
        config = self.client_configs[client_id]
        hashes = []
        
        for table_idx in range(config.num_tables):
            # Compute hash for this table
            hash_bits = []
            
            for bit_idx in range(config.hash_size):
                # Dot product with random hyperplane
                dot_product = np.dot(vector, random_planes[table_idx, bit_idx])
                # Hash bit is 1 if positive, 0 if negative
                hash_bits.append(1 if dot_product >= 0 else 0)
            
            # Convert bit array to integer hash value
            hash_value = sum(bit * (2 ** i) for i, bit in enumerate(hash_bits))
            hashes.append(hash_value)
        
        return hashes
    
    def find_candidate_embeddings(self,
                                client_id: str,
                                query_hashes: List[int],
                                stored_hashes: Dict[Tuple[int, int], Set[str]],
                                min_matches: int = 1) -> Set[str]:
        """
        Find candidate embeddings using LSH hash matching
        
        Args:
            client_id: Client identifier
            query_hashes: LSH hashes of query vector
            stored_hashes: Dictionary mapping (table_idx, hash_value) -> set of embedding_ids
            min_matches: Minimum number of table matches required
            
        Returns:
            Set of candidate embedding IDs
        """
        config = self.client_configs.get(client_id)
        if not config:
            raise ValueError(f"No LSH config found for client {client_id}")
        
        # Count matches for each embedding
        embedding_matches: Dict[str, int] = {}
        
        for table_idx, hash_value in enumerate(query_hashes):
            if table_idx >= config.num_tables:
                break
                
            # Find embeddings with matching hash in this table
            key = (table_idx, hash_value)
            matching_embeddings = stored_hashes.get(key, set())
            
            for embedding_id in matching_embeddings:
                embedding_matches[embedding_id] = embedding_matches.get(embedding_id, 0) + 1
        
        # Filter embeddings with sufficient matches
        candidates = {
            embedding_id for embedding_id, matches in embedding_matches.items()
            if matches >= min_matches
        }
        
        logger.info(f"Found {len(candidates)} candidates from {len(embedding_matches)} "
                   f"total matches (min_matches={min_matches})")
        
        return candidates
    
    def estimate_similarity_from_hashes(self,
                                      hash1: List[int],
                                      hash2: List[int]) -> float:
        """
        Estimate cosine similarity from LSH hashes
        Based on the fraction of matching hash bits
        
        Args:
            hash1: LSH hashes of first vector
            hash2: LSH hashes of second vector
            
        Returns:
            Estimated cosine similarity (0 to 1)
        """
        if len(hash1) != len(hash2):
            raise ValueError("Hash lists must have same length")
        
        total_bits = 0
        matching_bits = 0
        
        for h1, h2 in zip(hash1, hash2):
            # Count matching bits between the two hashes
            xor_result = h1 ^ h2
            hash_size = max(h1.bit_length(), h2.bit_length(), 1)
            
            # Count number of 0 bits in XOR (matching bits)
            matches = hash_size - bin(xor_result).count('1')
            
            matching_bits += matches
            total_bits += hash_size
        
        if total_bits == 0:
            return 0.0
        
        # Convert bit match ratio to estimated cosine similarity
        bit_match_ratio = matching_bits / total_bits
        
        # Empirical mapping from bit matches to cosine similarity
        # This is an approximation - actual relationship depends on hash size
        estimated_similarity = max(0.0, min(1.0, 2 * bit_match_ratio - 0.5))
        
        return estimated_similarity
    
    def get_client_config(self, client_id: str) -> Optional[LSHConfig]:
        """Get LSH configuration for a client"""
        return self.client_configs.get(client_id)
    
    def clear_client_data(self, client_id: str):
        """Clear all data for a client"""
        self.client_configs.pop(client_id, None)
        self.random_planes_cache.pop(client_id, None)
        logger.info(f"Cleared LSH data for client {client_id}")


# Global service instance
lsh_service = LSHSearchService()