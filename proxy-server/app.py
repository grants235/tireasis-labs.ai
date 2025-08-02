import os
import httpx
from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# Configuration
security = HTTPBearer()
PROXY_API_KEY = os.getenv("PROXY_API_KEY", "default_proxy_key")

# FastAPI app
app = FastAPI(
    title="Proxy Server", 
    description="Proxy service for external third-party APIs", 
    version="1.0.0"
)

# Pydantic models
class ExternalAPIRequest(BaseModel):
    url: str
    method: str = "GET"
    headers: Optional[Dict[str, str]] = None
    data: Optional[Dict[str, Any]] = None
    timeout: Optional[int] = 30

class ProxyResponse(BaseModel):
    status_code: int
    headers: Dict[str, str]
    content: str
    success: bool

# Security dependency
def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    if credentials.credentials != PROXY_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials.credentials

# Health check
@app.get("/health")
async def health_check():
    """Check proxy server health and external connectivity"""
    try:
        # Test external connectivity
        async with httpx.AsyncClient() as client:
            response = await client.get("https://httpbin.org/get", timeout=5.0)
            external_status = "connected" if response.status_code == 200 else "failed"
    except Exception:
        external_status = "failed"
    
    # Always return healthy status - external connectivity is informational only
    return {
        "status": "healthy",
        "service": "proxy-server",
        "external_connectivity": external_status,
        "version": "1.0.0"
    }

# External API proxy endpoint
@app.post("/proxy", response_model=ProxyResponse)
async def proxy_request(
    request: ExternalAPIRequest,
    api_key: str = Depends(verify_api_key)
):
    """Proxy requests to external third-party APIs"""
    async with httpx.AsyncClient() as client:
        try:
            headers = request.headers or {}
            timeout = request.timeout or 30
            
            if request.method.upper() == "GET":
                response = await client.get(
                    request.url, 
                    headers=headers, 
                    timeout=timeout
                )
            elif request.method.upper() == "POST":
                response = await client.post(
                    request.url, 
                    headers=headers, 
                    json=request.data,
                    timeout=timeout
                )
            elif request.method.upper() == "PUT":
                response = await client.put(
                    request.url, 
                    headers=headers, 
                    json=request.data,
                    timeout=timeout
                )
            elif request.method.upper() == "DELETE":
                response = await client.delete(
                    request.url, 
                    headers=headers,
                    timeout=timeout
                )
            elif request.method.upper() == "PATCH":
                response = await client.patch(
                    request.url, 
                    headers=headers, 
                    json=request.data,
                    timeout=timeout
                )
            else:
                raise HTTPException(status_code=400, detail="Unsupported HTTP method")
            
            return ProxyResponse(
                status_code=response.status_code,
                headers=dict(response.headers),
                content=response.text,
                success=200 <= response.status_code < 300
            )
            
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="External API request timed out")
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"External API request failed: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Proxy error: {str(e)}")

# Convenience endpoint for simple GET requests
@app.get("/proxy/{path:path}")
async def proxy_get(
    path: str,
    api_key: str = Depends(verify_api_key)
):
    """Simple GET proxy endpoint"""
    # Reconstruct full URL from path
    if not path.startswith("http"):
        raise HTTPException(status_code=400, detail="Path must be a complete URL starting with http/https")
    
    request = ExternalAPIRequest(url=path, method="GET")
    return await proxy_request(request, api_key)

# Test connectivity endpoint
@app.get("/test-connectivity")
async def test_external_connectivity(api_key: str = Depends(verify_api_key)):
    """Test external internet connectivity with various services"""
    test_urls = [
        "https://httpbin.org/get",
        "https://api.github.com",
        "https://jsonplaceholder.typicode.com/posts/1"
    ]
    
    results = {}
    
    async with httpx.AsyncClient() as client:
        for url in test_urls:
            try:
                response = await client.get(url, timeout=10.0)
                results[url] = {
                    "status": "success",
                    "status_code": response.status_code,
                    "response_time_ms": int(response.elapsed.total_seconds() * 1000)
                }
            except Exception as e:
                results[url] = {
                    "status": "failed",
                    "error": str(e)
                }
    
    return {
        "service": "proxy-server",
        "connectivity_tests": results,
        "overall_status": "healthy" if any(r.get("status") == "success" for r in results.values()) else "degraded"
    }

# Info endpoint
@app.get("/info")
async def get_info():
    """Get service information"""
    return {
        "service": "Proxy Server",
        "version": "1.0.0",
        "description": "Proxy service for external third-party APIs",
        "endpoints": {
            "proxy": {
                "POST /proxy": "Proxy any HTTP request to external APIs",
                "GET /proxy/{url}": "Simple GET proxy for external URLs"
            },
            "utility": {
                "GET /health": "Service health check",
                "GET /test-connectivity": "Test connectivity to various external services",
                "GET /info": "Service information"
            }
        },
        "supported_methods": ["GET", "POST", "PUT", "DELETE", "PATCH"],
        "authentication": "Bearer token required for all endpoints"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PROXY_SERVER_PORT", 8002))
    uvicorn.run(app, host="0.0.0.0", port=port)