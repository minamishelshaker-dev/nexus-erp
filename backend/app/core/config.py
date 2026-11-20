"""
Nexus ERP - Core Configuration Module
=====================================

This module provides centralized configuration management using Pydantic Settings.
Supports environment variables, .env files, and provides type-safe configuration
access throughout the application.

Features:
- Environment-based configuration
- Validation of required settings
- Secure defaults for production
- Multi-tenant support configuration
"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application Settings Class
    
    All configuration values can be overridden via environment variables.
    Environment variables should be prefixed with the field name in uppercase.
    """
    
    # ========================================
    # Application Settings
    # ========================================
    APP_NAME: str = "Nexus ERP"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    
    # ========================================
    # Server Settings
    # ========================================
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # ========================================
    # Database Settings
    # ========================================
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    
    # ========================================
    # Redis Settings
    # ========================================
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # ========================================
    # Security Settings
    # ========================================
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v
    
    # ========================================
    # CORS Settings
    # ========================================
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    
    # ========================================
    # OAuth2 Settings
    # ========================================
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    MICROROSOFT_CLIENT_ID: Optional[str] = None
    MICROSOFT_CLIENT_SECRET: Optional[str] = None
    
    # ========================================
    # Email Settings
    # ========================================
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: str = "noreply@nexus-erp.com"
    EMAILS_FROM_NAME: str = "Nexus ERP"
    
    # ========================================
    # File Storage Settings
    # ========================================
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 10485760  # 10MB
    
    # ========================================
    # Celery Settings
    # ========================================
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    # ========================================
    # Multi-tenancy Settings
    # ========================================
    MULTI_TENANT_ENABLED: bool = True
    DEFAULT_TENANT_SCHEMA: str = "public"
    
    # ========================================
    # AI Settings (OpenAI)
    # ========================================
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    # ========================================
    # Stripe Settings
    # ========================================
    STRIPE_API_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    
    # ========================================
    # Logging Settings
    # ========================================
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/nexus_erp.log"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Uses lru_cache to ensure only one instance is created
    throughout the application lifecycle.
    
    Returns:
        Settings: Application settings instance
    """
    return Settings()


# Export settings instance for convenience
settings = get_settings()
