"""
Authentication dependencies
"""
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ...core.config import settings

security = HTTPBearer()


def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """
    Verify API key for authentication
    """
    if credentials.credentials != settings.DB_SERVER_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials.credentials