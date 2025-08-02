"""
Health check endpoints
"""
from fastapi import APIRouter, HTTPException

from ...core.database import test_connection

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check endpoint to verify database connectivity
    """
    if test_connection():
        return {"status": "healthy", "database": "connected"}
    else:
        raise HTTPException(status_code=503, detail="Database connection failed")