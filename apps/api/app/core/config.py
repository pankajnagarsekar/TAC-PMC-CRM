from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os

class Settings(BaseSettings):
    """System Constitution: Configuration Sovereignty (Point 1, 37)"""
    PROJECT_NAME: str = "TAC-PMC-CRM"
    VERSION: str = "2.1.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    
    # MongoDB (Point 7, 12, 123)
    MONGO_URL: str = "mongodb://localhost:27017"
    DB_NAME: str = "tac_pmc_crm"
    
    # Security (Point 15, 22, 101, 116)
    JWT_SECRET_KEY: str = "DEV_INSECURE_SECRET_CHANGE_ME"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # STORAGE & AI (Point 21, 73, 110)
    STORAGE_PATH: str = "storage"
    UPLOAD_MAX_SIZE: int = 10 * 1024 * 1024 # 10MB (Point 114)
    
    # REDIS (For Rate Limiting / Shared State - Point 116)
    REDIS_URL: Optional[str] = None

    model_config = SettingsConfigDict(
        case_sensitive=True, 
        env_file=".env", 
        extra="ignore"
    )

# Singleton access is permitted for registry, but dependency injection is preferred for logic.
settings = Settings()
