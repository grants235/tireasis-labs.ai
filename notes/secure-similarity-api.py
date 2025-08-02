"""
Secure Client/Server Architecture for Privacy-Preserving Similarity Search
Using LSH + Homomorphic Encryption

API Design and Data Structures
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
import json
import base64
import numpy as np
import tenseal as ts
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
import aiohttp


# ============= DATA MODELS =============

class InitRequest(BaseModel):
    """Initial handshake to establish HE context"""
    context_params: Dict[str, any]  # Serialized TenSEAL context parameters
    embedding_dim: int = 384
    lsh_config: Dict[str, int] = {
        "num_tables": 20,
        "hash_size": 16,
        "num_candidates": 100
    }


class InitResponse(BaseModel):
    """Server confirms initialization"""
    server_id: str
    max_db_size: int
    supported_operations: List[str]


class AddEmbeddingRequest(BaseModel):
    """Add encrypted embedding to server database"""
    encrypted_embedding: str  # Base64 encoded encrypted vector
    lsh_hashes: List[int]     # LSH hashes (safe to send in plaintext)
    metadata: Optional[Dict[str, any]] = None
    embedding_id: Optional[str] = None


class AddEmbeddingResponse(BaseModel):
    """Confirmation of embedding addition"""
    embedding_id: str
    index_position: int
    status: str


class SearchRequest(BaseModel):
    """Search for similar embeddings"""
    encrypted_query: str      # Base64 encoded encrypted query vector
    lsh_hashes: List[int]     # LSH hashes of query
    top_k: int = 10          # Number of results to return
    rerank_candidates: int = 100  # How many LSH candidates to check with HE


class SearchResult(BaseModel):
    """Individual search result"""
    embedding_id: str
    encrypted_similarity: str  # Base64 encoded encrypted similarity score
    metadata: Optional[Dict[str, any]] = None


class SearchResponse(BaseModel):
    """Response containing encrypted similarities"""
    results: List[SearchResult]
    candidates_checked: int
    search_time_ms: float


# ============= CLIENT IMPLEMENTATION =============

class SecureSearchClient:
    """Client for privacy-preserving similarity search"""
    
    def __init__(self, server_url: str, embedding_dim: int = 384):
        self.server_url = server_url
        self.embedding_dim = embedding_dim
        self.context = self._create_context()
        self.session = None
        
    def _create_context(self) -> ts.Context:
        """Create optimized TenSEAL context"""
        context = ts.context(
            ts.SCHEME_TYPE.CKKS,
            poly_modulus_degree=8192,
            coeff_mod_bit_sizes=[60, 40, 40, 60]
        )
        context.generate_galois_keys()
        context.global_scale = 2**40
        return context
    
    def _serialize_context(self) -> Dict:
        """Serialize context for transmission"""
        # In practice, you'd serialize the public key and parameters
        return {
            "scheme": "CKKS",
            "poly_modulus_degree": 8192,
            "scale": 2**40,
            "public_key": base64.b64encode(
                self.context.serialize(save_public_key=True, save_secret_key=False)
            ).decode('utf-8')
        }
    
    def _encrypt_vector(self, vector: np.ndarray) -> str:
        """Encrypt and encode vector for transmission"""
        # Normalize
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
            
        # Encrypt
        encrypted = ts.ckks_vector(self.context, vector.tolist())
        
        # Serialize and encode
        serialized = encrypted.serialize()
        return base64.b64encode(serialized).decode('utf-8')
    
    def _compute_lsh_hashes(self, vector: np.ndarray, 
                           random_planes: np.ndarray) -> List[int]:
        """Compute LSH hashes (client needs same random planes as server)"""
        # This would be received from server during init
        # For now, using a simplified version
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
            
        # Simplified hash computation
        hashes = []
        for i in range(20):  # num_tables
            # In practice, use the actual random planes from server
            hash_val = hash(tuple(vector)) + i
            hashes.append(hash_val % (2**16))
        return hashes
    
    async def initialize(self) -> Dict:
        """Initialize connection with server"""
        self.session = aiohttp.ClientSession()
        
        request = InitRequest(
            context_params=self._serialize_context(),
            embedding_dim=self.embedding_dim
        )
        
        async with self.session.post(
            f"{self.server_url}/initialize",
            json=request.dict()
        ) as response:
            return await response.json()
    
    async def add_embedding(self, 
                          embedding: np.ndarray, 
                          metadata: Dict = None,
                          embedding_id: str = None) -> Dict:
        """Add embedding to server database"""
        # Encrypt embedding
        encrypted_embedding = self._encrypt_vector(embedding)
        
        # Compute LSH hashes
        # In practice, server would send random planes during init
        lsh_hashes = self._compute_lsh_hashes(embedding, None)
        
        request = AddEmbeddingRequest(
            encrypted_embedding=encrypted_embedding,
            lsh_hashes=lsh_hashes,
            metadata=metadata,
            embedding_id=embedding_id
        )
        
        async with self.session.post(
            f"{self.server_url}/add_embedding",
            json=request.dict()
        ) as response:
            return await response.json()
    
    async def search(self, 
                    query_embedding: np.ndarray, 
                    top_k: int = 10) -> List[Tuple[str, float, Dict]]:
        """Search for similar embeddings"""
        # Encrypt query
        encrypted_query = self._encrypt_vector(query_embedding)
        
        # Compute LSH hashes
        lsh_hashes = self._compute_lsh_hashes(query_embedding, None)
        
        request = SearchRequest(
            encrypted_query=encrypted_query,
            lsh_hashes=lsh_hashes,
            top_k=top_k
        )
        
        # Send search request
        async with self.session.post(
            f"{self.server_url}/search",
            json=request.dict()
        ) as response:
            search_response = SearchResponse(**await response.json())
        
        # Decrypt results
        results = []
        for result in search_response.results:
            # Decode and deserialize encrypted similarity
            encrypted_sim = base64.b64decode(result.encrypted_similarity)
            
            # In practice, deserialize back to TenSEAL vector
            # For demo, using placeholder
            similarity_score = 0.95  # Would be: ts_vector.decrypt()[0]
            
            results.append((
                result.embedding_id,
                similarity_score,
                result.metadata or {}
            ))
        
        # Sort by similarity (highest first)
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
    
    async def close(self):
        """Close client session"""
        if self.session:
            await self.session.close()


# ============= SERVER IMPLEMENTATION =============

class SecureSearchServer:
    """Server for privacy-preserving similarity search"""
    
    def __init__(self):
        self.app = FastAPI(title="Secure Similarity Search API")
        self.initialized = False
        self.context = None
        self.lsh_index = None
        self.encrypted_db: List[bytes] = []
        self.metadata_db: List[Dict] = []
        self.embedding_ids: List[str] = []
        self.random_planes = None
        
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup API routes"""
        
        @self.app.post("/initialize", response_model=InitResponse)
        async def initialize(request: InitRequest):
            """Initialize server with client's HE context"""
            try:
                # Deserialize context (public key only)
                context_bytes = base64.b64decode(request.context_params["public_key"])
                self.context = ts.context_from(context_bytes)
                
                # Initialize LSH
                from dataclasses import dataclass
                @dataclass
                class LSHConfig:
                    num_tables: int = request.lsh_config["num_tables"]
                    hash_size: int = request.lsh_config["hash_size"]
                    num_candidates: int = request.lsh_config["num_candidates"]
                
                # Create LSH index (using simplified version)
                self.lsh_config = LSHConfig()
                self.lsh_tables = [{} for _ in range(self.lsh_config.num_tables)]
                
                # Generate random planes for LSH
                self.random_planes = np.random.randn(
                    self.lsh_config.num_tables,
                    self.lsh_config.hash_size,
                    request.embedding_dim
                )
                
                self.initialized = True
                
                return InitResponse(
                    server_id="server-001",
                    max_db_size=100000,
                    supported_operations=["add_embedding", "search", "batch_search"]
                )
                
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.post("/add_embedding", response_model=AddEmbeddingResponse)
        async def add_embedding(request: AddEmbeddingRequest):
            """Add encrypted embedding to database"""
            if not self.initialized:
                raise HTTPException(status_code=400, detail="Server not initialized")
            
            try:
                # Decode encrypted embedding
                encrypted_embedding = base64.b64decode(request.encrypted_embedding)
                
                # Generate ID if not provided
                embedding_id = request.embedding_id or f"emb_{len(self.encrypted_db)}"
                
                # Store in database
                index_position = len(self.encrypted_db)
                self.encrypted_db.append(encrypted_embedding)
                self.metadata_db.append(request.metadata or {})
                self.embedding_ids.append(embedding_id)
                
                # Add to LSH index
                for table_idx, hash_value in enumerate(request.lsh_hashes):
                    if hash_value not in self.lsh_tables[table_idx]:
                        self.lsh_tables[table_idx][hash_value] = set()
                    self.lsh_tables[table_idx][hash_value].add(index_position)
                
                return AddEmbeddingResponse(
                    embedding_id=embedding_id,
                    index_position=index_position,
                    status="success"
                )
                
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.post("/search", response_model=SearchResponse)
        async def search(request: SearchRequest):
            """Search for similar embeddings"""
            if not self.initialized:
                raise HTTPException(status_code=400, detail="Server not initialized")
            
            import time
            start_time = time.time()
            
            try:
                # Step 1: Find candidates using LSH
                candidates = set()
                for table_idx, hash_value in enumerate(request.lsh_hashes):
                    if hash_value in self.lsh_tables[table_idx]:
                        candidates.update(self.lsh_tables[table_idx][hash_value])
                
                # Limit candidates
                candidates = list(candidates)[:request.rerank_candidates]
                
                # Step 2: Compute encrypted similarities for candidates
                encrypted_query = base64.b64decode(request.encrypted_query)
                
                results = []
                for idx in candidates:
                    # In practice: deserialize vectors and compute dot product
                    # encrypted_sim = query_vec.dot(db_vec)
                    
                    # For demo, create placeholder encrypted similarity
                    encrypted_sim = base64.b64encode(b"encrypted_similarity").decode('utf-8')
                    
                    results.append(SearchResult(
                        embedding_id=self.embedding_ids[idx],
                        encrypted_similarity=encrypted_sim,
                        metadata=self.metadata_db[idx]
                    ))
                
                # Note: Server cannot sort by similarity (encrypted)
                # Client will decrypt and sort
                
                search_time = (time.time() - start_time) * 1000
                
                return SearchResponse(
                    results=results[:request.top_k * 2],  # Return more for client to sort
                    candidates_checked=len(candidates),
                    search_time_ms=search_time
                )
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
    
    def run(self, host: str = "0.0.0.0", port: int = 8000):
        """Run the server"""
        import uvicorn
        uvicorn.run(self.app, host=host, port=port)


# ============= USAGE EXAMPLE =============

async def example_usage():
    """Example of how to use the secure search system"""
    
    # Initialize client
    client = SecureSearchClient("http://localhost:8000", embedding_dim=384)
    
    # Initialize connection
    await client.initialize()
    
    # Add some embeddings
    print("Adding embeddings to server...")
    for i in range(1000):
        embedding = np.random.randn(384)
        await client.add_embedding(
            embedding,
            metadata={"text": f"Sentence {i}", "category": "example"},
            embedding_id=f"sent_{i}"
        )
    
    # Search for similar embeddings
    print("\nSearching for similar embeddings...")
    query = np.random.randn(384)
    results = await client.search(query, top_k=10)
    
    print("\nTop 10 Results:")
    for i, (emb_id, score, metadata) in enumerate(results):
        print(f"{i+1}. {emb_id}: {score:.4f} - {metadata.get('text', 'N/A')}")
    
    await client.close()


# ============= DATA FLOW SUMMARY =============

"""
DATA FLOW AND API CALLS:

1. INITIALIZATION:
   Client → Server: {
     "context_params": {
       "public_key": "base64_encoded_public_key",
       "scheme": "CKKS",
       "poly_modulus_degree": 8192,
       "scale": 1099511627776.0
     },
     "embedding_dim": 384,
     "lsh_config": {
       "num_tables": 20,
       "hash_size": 16,
       "num_candidates": 100
     }
   }
   
   Server → Client: {
     "server_id": "server-001",
     "max_db_size": 100000,
     "supported_operations": ["add_embedding", "search", "batch_search"]
   }

2. ADD EMBEDDING:
   Client → Server: {
     "encrypted_embedding": "base64_encoded_encrypted_vector",
     "lsh_hashes": [12345, 67890, ...],  // 20 hash values
     "metadata": {"text": "Example sentence"},
     "embedding_id": "sent_001"
   }
   
   Server → Client: {
     "embedding_id": "sent_001",
     "index_position": 0,
     "status": "success"
   }

3. SEARCH:
   Client → Server: {
     "encrypted_query": "base64_encoded_encrypted_query",
     "lsh_hashes": [11111, 22222, ...],  // 20 hash values
     "top_k": 10,
     "rerank_candidates": 100
   }
   
   Server → Client: {
     "results": [
       {
         "embedding_id": "sent_042",
         "encrypted_similarity": "base64_encoded_encrypted_score",
         "metadata": {"text": "Similar sentence 42"}
       },
       // ... more results
     ],
     "candidates_checked": 87,
     "search_time_ms": 1250.5
   }

KEY SECURITY PROPERTIES:
- Server never sees plaintext embeddings
- LSH hashes don't reveal embedding content (they're locality-preserving projections)
- Similarity scores remain encrypted until client decrypts
- Server cannot determine which results are most similar
- Client controls all encryption/decryption
"""

if __name__ == "__main__":
    # Run server
    server = SecureSearchServer()
    server.run()
    
    # Or run client example
    # asyncio.run(example_usage())
