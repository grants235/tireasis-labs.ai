"""
Core configuration settings for the Secure Search DB Server
"""
import os
from typing import Optional
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application settings"""
    
    # Database Configuration
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "app_user")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "password")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "postgres")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "app_database")
    
    # Security
    DB_SERVER_API_KEY: str = os.getenv("DB_SERVER_API_KEY", "default_key")
    
    # Server Configuration
    DB_SERVER_PORT: int = int(os.getenv("DB_SERVER_PORT", 8001))
    HOST: str = "0.0.0.0"
    
    # Application Settings
    APP_NAME: str = "Secure Search DB Server"
    APP_DESCRIPTION: str = "Database service for secure similarity search"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    @property
    def database_url(self) -> str:
        """Construct database URL"""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    class Config:
        env_file = ".env"


# Global settings instance
settings = Settings()