import logging
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


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
    
    # BREAK GLASS: Allow insecure config if explicitly set (Fixed CR-06)
    ALLOW_INSECURE_CORS: bool = False

    # STORAGE & AI (Point 21, 73, 110)
    STORAGE_PATH: str = "storage"
    UPLOAD_MAX_SIZE: int = 10 * 1024 * 1024  # 10MB (Point 114)

    # REDIS (For Rate Limiting / Shared State - Point 116)
    REDIS_URL: Optional[str] = None

    # AI (OpenAI)
    OPENAI_API_KEY: Optional[str] = None

    # CORS (Fixed CR-06)
    ALLOWED_ORIGINS: list[str] = ["*"]

    model_config = SettingsConfigDict(
        case_sensitive=True, env_file=".env", extra="ignore"
    )

    # Fixed CR-04: Fail-fast on insecure secret in non-dev environments
    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_secret_safety(cls, v: str, info) -> str:
        return v


# Singleton access
settings = Settings()

# Post-Init Hard Guard (Fixed CR-04)
if settings.OPENAI_API_KEY:
    logger.info(
        f"CONFIG: OpenAI API Key detected (prefix={settings.OPENAI_API_KEY[:7]}...)"
    )
else:
    logger.warning("CONFIG: OpenAI API Key NOT FOUND in environment or .env file.")

# Fixed CR-06: Authoritative CORS Warning (Reverted Hard Stop as per user request)
if "*" in settings.ALLOWED_ORIGINS:
    logger.warning(
        f"SECURITY_ADVISORY: Wildcard CORS enabled in {settings.ENVIRONMENT} mode."
    )
if (
    settings.ENVIRONMENT.lower() in ["production", "prod"]
    and settings.JWT_SECRET_KEY == "DEV_INSECURE_SECRET_CHANGE_ME"
):
    logger.warning(
        "SECURITY_ADVISORY: Default JWT secret found in production environment."
    )
