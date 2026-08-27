import os
from typing import Literal, Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    PROJECT_NAME: str = "RazorGuard AI"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    PORT: int = 8000
    API_PREFIX: str = "/api/v1"

    # Database connection URL
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/razorguard_db"

    # Security
    SECRET_KEY: Optional[str] = None
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALLOW_FIRST_USER_ADMIN: bool = False

    # CORS Origins
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # AI Configurations
    LLM_PROVIDER: Literal["gemini", "mock"] = "mock"
    GEMINI_API_KEY: Optional[str] = None

    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    LOCAL_STORAGE_PATH: str = "./data/storage"

    @model_validator(mode="after")
    def validate_secret_key(self) -> "Settings":
        if not self.SECRET_KEY:
            if self.ENVIRONMENT == "production":
                raise ValueError("CRITICAL SECURITY ERROR: SECRET_KEY environment variable is not configured for production mode!")
            else:
                # Pin to a fixed default key in non-production modes for session/token reproducibility during development/testing
                self.SECRET_KEY = "insecure-development-fallback-key-should-be-replaced-in-env"
        return self
        

settings = Settings()
