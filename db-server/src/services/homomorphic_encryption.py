"""
Homomorphic Encryption Service using TenSEAL
Provides secure computation of similarity scores on encrypted vectors
"""
import base64
import json
import numpy as np
from typing import List, Tuple, Optional, Dict, Any
import tenseal as ts
import logging

logger = logging.getLogger(__name__)


class HomomorphicEncryptionService:
    """
    Service for homomorphic encryption operations using CKKS scheme
    Enables computation on encrypted vectors while preserving privacy
    """
    
    def __init__(self):
        self.context_cache: Dict[str, ts.TenSEALContext] = {}
        
    def create_context(self, 
                      poly_modulus_degree: int = 8192,
                      coeff_mod_bit_sizes: List[int] = None,
                      scale: float = 2**40) -> ts.TenSEALContext:
        """
        Create a new TenSEAL context for CKKS scheme
        
        Args:
            poly_modulus_degree: Polynomial modulus degree (power of 2)
            coeff_mod_bit_sizes: Coefficient modulus bit sizes 
            scale: Scale for CKKS encoding
            
        Returns:
            TenSEAL context for homomorphic operations
        """
        if coeff_mod_bit_sizes is None:
            coeff_mod_bit_sizes = [60, 40, 40, 60]
            
        context = ts.context(
            ts.SCHEME_TYPE.CKKS,
            poly_modulus_degree=poly_modulus_degree,
            coeff_mod_bit_sizes=coeff_mod_bit_sizes
        )
        
        # Set the scale
        context.global_scale = scale
        
        # Generate galois keys for rotations (needed for dot product)
        context.generate_galois_keys()
        
        logger.info(f"Created HE context with poly_degree={poly_modulus_degree}")
        return context
    
    def serialize_context(self, context: ts.TenSEALContext) -> str:
        """Serialize context to base64 string"""
        context_bytes = context.serialize()
        return base64.b64encode(context_bytes).decode('utf-8')
    
    def deserialize_context(self, context_b64: str) -> ts.TenSEALContext:
        """Deserialize context from base64 string"""
        context_bytes = base64.b64decode(context_b64.encode('utf-8'))
        return ts.context_from(context_bytes)
    
    def cache_context(self, client_id: str, context: ts.TenSEALContext):
        """Cache context for client to avoid repeated deserialization"""
        self.context_cache[client_id] = context
        logger.info(f"Cached HE context for client {client_id}")
    
    def get_cached_context(self, client_id: str) -> Optional[ts.TenSEALContext]:
        """Get cached context for client"""
        return self.context_cache.get(client_id)
    
    def encrypt_vector(self, context: ts.TenSEALContext, vector: np.ndarray) -> str:
        """
        Encrypt a vector using CKKS scheme
        
        Args:
            context: TenSEAL context
            vector: Numpy array to encrypt
            
        Returns:
            Base64 encoded encrypted vector
        """
        # Ensure vector is float64 for CKKS
        vector = vector.astype(np.float64)
        
        # Encrypt the vector
        encrypted_vector = ts.ckks_vector(context, vector.tolist())
        
        # Serialize and encode
        encrypted_bytes = encrypted_vector.serialize()
        return base64.b64encode(encrypted_bytes).decode('utf-8')
    
    def deserialize_encrypted_vector(self, 
                                   context: ts.TenSEALContext, 
                                   encrypted_vector_b64: str) -> ts.CKKSVector:
        """
        Deserialize an encrypted vector
        
        Args:
            context: TenSEAL context
            encrypted_vector_b64: Base64 encoded encrypted vector
            
        Returns:
            TenSEAL CKKSVector object
        """
        encrypted_bytes = base64.b64decode(encrypted_vector_b64.encode('utf-8'))
        return ts.ckks_vector_from(context, encrypted_bytes)
    
    def compute_encrypted_similarity(self, 
                                   context: ts.TenSEALContext,
                                   encrypted_query: str,
                                   encrypted_vector: str) -> str:
        """
        Compute similarity score between two encrypted vectors
        Uses homomorphic dot product computation
        
        Args:
            context: TenSEAL context
            encrypted_query: Base64 encoded encrypted query vector  
            encrypted_vector: Base64 encoded encrypted stored vector
            
        Returns:
            Base64 encoded encrypted similarity score
        """
        try:
            # Deserialize encrypted vectors
            query_vec = self.deserialize_encrypted_vector(context, encrypted_query)
            stored_vec = self.deserialize_encrypted_vector(context, encrypted_vector)
            
            # Compute homomorphic dot product
            # This performs encrypted multiplication and sum
            dot_product = query_vec.dot(stored_vec)
            
            # Serialize the result
            result_bytes = dot_product.serialize()
            return base64.b64encode(result_bytes).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Failed to compute encrypted similarity: {e}")
            raise
    
    def batch_encrypt_vectors(self, 
                            context: ts.TenSEALContext, 
                            vectors: List[np.ndarray]) -> List[str]:
        """
        Batch encrypt multiple vectors for efficiency
        
        Args:
            context: TenSEAL context
            vectors: List of numpy arrays to encrypt
            
        Returns:
            List of base64 encoded encrypted vectors
        """
        encrypted_vectors = []
        
        for i, vector in enumerate(vectors):
            try:
                encrypted = self.encrypt_vector(context, vector)
                encrypted_vectors.append(encrypted)
                
                if (i + 1) % 100 == 0:
                    logger.info(f"Encrypted {i + 1}/{len(vectors)} vectors")
                    
            except Exception as e:
                logger.error(f"Failed to encrypt vector {i}: {e}")
                encrypted_vectors.append(None)
        
        return encrypted_vectors
    
    def batch_compute_similarities(self,
                                 context: ts.TenSEALContext,
                                 encrypted_query: str,
                                 encrypted_vectors: List[str]) -> List[str]:
        """
        Batch compute similarities for multiple encrypted vectors
        
        Args:
            context: TenSEAL context
            encrypted_query: Base64 encoded encrypted query
            encrypted_vectors: List of base64 encoded encrypted vectors
            
        Returns:
            List of base64 encoded encrypted similarity scores
        """
        similarities = []
        
        for i, encrypted_vec in enumerate(encrypted_vectors):
            try:
                if encrypted_vec is None:
                    similarities.append(None)
                    continue
                    
                similarity = self.compute_encrypted_similarity(
                    context, encrypted_query, encrypted_vec
                )
                similarities.append(similarity)
                
                if (i + 1) % 50 == 0:
                    logger.info(f"Computed {i + 1}/{len(encrypted_vectors)} similarities")
                    
            except Exception as e:
                logger.error(f"Failed to compute similarity {i}: {e}")
                similarities.append(None)
        
        return similarities
    
    def clear_context_cache(self, client_id: Optional[str] = None):
        """
        Clear cached contexts
        
        Args:
            client_id: If provided, clear only this client's context.
                      If None, clear all contexts.
        """
        if client_id:
            self.context_cache.pop(client_id, None)
            logger.info(f"Cleared cached context for client {client_id}")
        else:
            self.context_cache.clear()
            logger.info("Cleared all cached contexts")


# Global service instance
he_service = HomomorphicEncryptionService()