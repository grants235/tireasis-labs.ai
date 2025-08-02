"""
Legacy app.py - redirects to new modular structure

This file maintains backward compatibility while using the new modular structure.
"""
import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.main import app

if __name__ == "__main__":
    import uvicorn
    from src.core.config import settings
    uvicorn.run(app, host=settings.HOST, port=settings.DB_SERVER_PORT)