"""
API routes for the secure search database server
"""
from fastapi import APIRouter

from .health import router as health_router
from .clients import router as clients_router
from .lsh import router as lsh_router
from .embeddings import router as embeddings_router
from .search import router as search_router
from .secure_search import router as secure_search_router
from .lsh_management import router as lsh_management_router

# Main API router
api_router = APIRouter()

# Include all route modules
api_router.include_router(health_router)
api_router.include_router(clients_router)
api_router.include_router(lsh_router)
api_router.include_router(embeddings_router)
api_router.include_router(search_router)

# Secure search API endpoints (main functionality)
api_router.include_router(secure_search_router)
api_router.include_router(lsh_management_router)