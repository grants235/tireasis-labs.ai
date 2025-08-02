"""
Secure Search Client for testing the privacy-preserving similarity search system
Simulates homomorphic encryption and LSH for testing purposes
"""
import uuid
import base64
import hashlib
import time
import json
from typing import List, Dict, Optional, Tuple, Any
import numpy as np
import requests
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, TaskID


class SecureSearchTestClient:
    """
    Test client that simulates the secure search workflow
    Uses mock encryption for testing (in production would use TenSEAL/SEAL)
    """
    
    def __init__(self, server_url: str = "http://secure-search-vm-1754105923.eastus.cloudapp.azure.com:8001", api_key: str = "TSJnSyPxW5OZCIoNoCZ72KONxttNfDoNS8qbZkr3Oa8="):
        self.server_url = server_url
        self.api_key = api_key
        self.client_id: Optional[uuid.UUID] = None
        self.embedding_dim = 384
        self.console = Console()
        
        # LSH parameters (must match server configuration)
        self.lsh_config = {
            "num_tables": 20,
            "hash_size": 16,
            "num_candidates": 100
        }
        
        # Simulated random planes for LSH (in production, server would provide these)
        np.random.seed(42)  # For reproducible results
        self.random_planes = np.random.randn(
            self.lsh_config["num_tables"], 
            self.lsh_config["hash_size"], 
            self.embedding_dim
        )
        
        self.console.print("[bold blue]🔐 Secure Search Test Client Initialized[/bold blue]")
        self.console.print(f"Server URL: {server_url}")
        self.console.print(f"Embedding Dimension: {self.embedding_dim}")
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make HTTP request to server with proper authentication"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.server_url}{endpoint}"
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=30)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            self.console.print(f"[red]❌ Request failed: {e}[/red]")
            raise

    def _simulate_encrypt_vector(self, vector: np.ndarray) -> str:
        """
        Simulate encryption of a vector using mock HE
        In production, this would use TenSEAL CKKS encryption
        """
        # Normalize vector
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        
        # Mock encryption: base64 encode the vector with some "encryption" metadata
        mock_encrypted = {
            "scheme": "CKKS_MOCK",
            "vector_data": vector.tolist(),
            "timestamp": time.time(),
            "client_id": str(self.client_id) if self.client_id else "uninitialized"
        }
        
        encrypted_bytes = json.dumps(mock_encrypted).encode()
        return base64.b64encode(encrypted_bytes).decode('utf-8')
    
    def _compute_lsh_hashes(self, vector: np.ndarray) -> List[int]:
        """
        Compute LSH hashes for a vector using random hyperplanes
        This is the same computation that would be done client-side in production
        """
        # Normalize vector
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        
        hashes = []
        for table_idx in range(self.lsh_config["num_tables"]):
            # Compute hash for this table using random hyperplanes
            hash_bits = []
            for bit_idx in range(self.lsh_config["hash_size"]):
                # Dot product with random hyperplane
                dot_product = np.dot(vector, self.random_planes[table_idx, bit_idx])
                hash_bits.append(1 if dot_product >= 0 else 0)  # Use >= 0 to match server
            
            # Convert bits to integer hash value
            hash_value = sum(bit * (2 ** i) for i, bit in enumerate(hash_bits))
            hashes.append(hash_value)
        
        return hashes
    
    def _text_to_vector(self, text: str) -> np.ndarray:
        """
        Convert text to a mock embedding vector
        In production, this would use a real embedding model like sentence-transformers
        """
        # Create a deterministic but pseudo-random embedding based on text
        # This simulates what a real embedding model would produce
        hash_obj = hashlib.sha256(text.encode())
        seed = int(hash_obj.hexdigest()[:8], 16)
        
        np.random.seed(seed)
        vector = np.random.randn(self.embedding_dim)
        
        # Add some semantic similarity by incorporating word hashes
        words = text.lower().split()
        for word in words:
            word_hash = int(hashlib.md5(word.encode()).hexdigest()[:8], 16)
            np.random.seed(word_hash)
            word_vector = np.random.randn(self.embedding_dim) * 0.1
            vector += word_vector
        
        # Normalize
        return vector / np.linalg.norm(vector)
    
    def initialize(self) -> Dict:
        """Initialize client with server - establish HE context"""
        self.console.print("\n[yellow]🚀 Initializing client with server...[/yellow]")
        
        # Create mock HE context parameters
        mock_context = {
            "public_key": base64.b64encode(f"mock_public_key_{time.time()}".encode()).decode(),
            "scheme": "CKKS",
            "poly_modulus_degree": 8192,
            "scale": 1099511627776
        }
        
        init_request = {
            "context_params": mock_context,
            "embedding_dim": self.embedding_dim,
            "lsh_config": self.lsh_config
        }
        
        response = self._make_request("POST", "/initialize", init_request)
        
        self.client_id = uuid.UUID(response["client_id"])
        
        # Use server-provided random planes for LSH consistency
        if "random_planes" in response and response["random_planes"]:
            import pickle
            random_planes_data = base64.b64decode(response["random_planes"])
            self.random_planes = pickle.loads(random_planes_data)
            self.console.print("[green]✅ Using server-synchronized LSH planes[/green]")
            
            # Update LSH config to match server
            lsh_config = response.get("lsh_config", {})
            if lsh_config:
                self.lsh_config.update(lsh_config)
                self.console.print(f"[green]✅ Synchronized LSH config: {lsh_config}[/green]")
        else:
            self.console.print("[yellow]⚠️ No random planes received from server, using client defaults[/yellow]")
        
        self.console.print(f"[green]✅ Client initialized successfully![/green]")
        self.console.print(f"Client ID: {self.client_id}")
        self.console.print(f"Server ID: {response['server_id']}")
        self.console.print(f"Max DB Size: {response['max_db_size']:,}")
        self.console.print(f"Supported Operations: {', '.join(response['supported_operations'])}")
        
        return response
    
    def add_embedding(self, text: str, embedding_id: Optional[str] = None, 
                     metadata: Optional[Dict] = None) -> Dict:
        """Add an encrypted embedding to the server"""
        if not self.client_id:
            raise ValueError("Client not initialized. Call initialize() first.")
        
        # Convert text to vector and encrypt
        vector = self._text_to_vector(text)
        encrypted_vector = self._simulate_encrypt_vector(vector)
        
        # Compute LSH hashes
        lsh_hashes = self._compute_lsh_hashes(vector)
        
        # Prepare metadata
        if metadata is None:
            metadata = {}
        metadata.update({
            "text": text,
            "text_length": len(text),
            "word_count": len(text.split()),
            "added_at": time.time()
        })
        
        add_request = {
            "client_id": str(self.client_id),
            "encrypted_embedding": encrypted_vector,
            "lsh_hashes": lsh_hashes,
            "metadata": metadata,
            "embedding_id": embedding_id
        }
        
        response = self._make_request("POST", "/add_embedding", add_request)
        return response
    
    def search(self, query_text: str, top_k: int = 5, rerank_candidates: int = 50) -> Dict:
        """Perform encrypted similarity search"""
        if not self.client_id:
            raise ValueError("Client not initialized. Call initialize() first.")
        
        # Convert query to vector and encrypt
        query_vector = self._text_to_vector(query_text)
        encrypted_query = self._simulate_encrypt_vector(query_vector)
        
        # Compute LSH hashes for query
        lsh_hashes = self._compute_lsh_hashes(query_vector)
        
        search_request = {
            "client_id": str(self.client_id),
            "encrypted_query": encrypted_query,
            "lsh_hashes": lsh_hashes,
            "top_k": top_k,
            "rerank_candidates": rerank_candidates
        }
        
        response = self._make_request("POST", "/search", search_request)
        
        # Simulate decryption of similarity scores (in production, client would decrypt)
        for result in response["results"]:
            # Mock decryption - in reality this would use the private key
            try:
                encrypted_sim = base64.b64decode(result["encrypted_similarity"]).decode()
                # Extract a mock similarity score (in production, this would be the decrypted score)
                mock_similarity = hash(encrypted_sim) % 1000 / 1000.0  # 0.0 to 1.0
                result["decrypted_similarity"] = mock_similarity
            except:
                result["decrypted_similarity"] = 0.5  # Fallback
        
        # Sort by decrypted similarity (client-side sorting)
        response["results"].sort(key=lambda x: x["decrypted_similarity"], reverse=True)
        response["results"] = response["results"][:top_k]
        
        return response
    
    def get_client_stats(self) -> Dict:
        """Get client statistics from server"""
        if not self.client_id:
            raise ValueError("Client not initialized. Call initialize() first.")
        
        return self._make_request("GET", f"/clients/{self.client_id}/stats")
    
    def print_search_results(self, query: str, results: Dict):
        """Pretty print search results"""
        self.console.print(f"\n[bold cyan]🔍 Search Results for: '{query}'[/bold cyan]")
        self.console.print(f"Candidates checked: {results['candidates_checked']}")
        self.console.print(f"Search time: {results['search_time_ms']:.2f}ms")
        
        if not results["results"]:
            self.console.print("[yellow]No results found[/yellow]")
            return
        
        table = Table(title="Search Results")
        table.add_column("Rank", style="cyan", no_wrap=True)
        table.add_column("Embedding ID", style="magenta")
        table.add_column("Similarity", style="green")
        table.add_column("Text", style="white")
        table.add_column("Category", style="yellow")
        
        for i, result in enumerate(results["results"], 1):
            embedding_id = str(result["embedding_id"])[:8] + "..."
            similarity = f"{result['decrypted_similarity']:.3f}"
            text = result["metadata"].get("text", "N/A")[:50] + "..." if len(result["metadata"].get("text", "")) > 50 else result["metadata"].get("text", "N/A")
            category = result["metadata"].get("category", "N/A")
            
            table.add_row(str(i), embedding_id, similarity, text, category)
        
        self.console.print(table)
    
    def print_stats(self):
        """Print client statistics"""
        if not self.client_id:
            self.console.print("[red]Client not initialized[/red]")
            return
        
        try:
            stats = self.get_client_stats()
            
            self.console.print("\n[bold green]📊 Client Statistics[/bold green]")
            self.console.print(f"Client ID: {stats['client_id']}")
            self.console.print(f"Client Name: {stats['client_name']}")
            self.console.print(f"Total Embeddings: {stats['total_embeddings']}")
            self.console.print(f"Total Searches: {stats['total_searches']}")
            self.console.print(f"Embedding Dimension: {stats['embedding_dim']}")
            self.console.print(f"Max Embeddings Allowed: {stats['max_embeddings_allowed']:,}")
            self.console.print(f"Last Active: {stats['last_active_at']}")
            self.console.print(f"Status: {'🟢 Active' if stats['is_active'] else '🔴 Inactive'}")
            
        except Exception as e:
            self.console.print(f"[red]❌ Failed to get stats: {e}[/red]")