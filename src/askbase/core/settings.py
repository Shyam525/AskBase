"""Configuration management and environment validation using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEVELOPMENT_JWT_SECRET = "local-development-secret-change-me-in-production-min-32-chars"


class Settings(BaseSettings):
    """Application settings with strict environment validation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Runtime Environment
    ENVIRONMENT: Literal["development", "test", "production"] = Field(
        default="development",
        validation_alias="NODE_ENV",
    )
    PORT: int = Field(default=5000, ge=1, le=65535)
    HOST: str = "0.0.0.0"

    # Database Configuration
    DATABASE_URL: str = Field(default="postgresql+asyncpg://postgres:secret@localhost:5432/askbase")
    DATABASE_POOL_MIN: int = Field(default=2, ge=1)
    DATABASE_POOL_MAX: int = Field(default=10, ge=1)
    DATABASE_ECHO: bool = False

    # Security & Cryptography
    JWT_SECRET: str = Field(default="")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRES_IN_MINUTES: int = Field(default=15, ge=1)
    JWT_REFRESH_EXPIRES_IN_DAYS: int = Field(default=7, ge=1)
    JWT_ISSUER: str = "askbase-api"
    JWT_AUDIENCE: str = "askbase-clients"

    # Argon2 Password Hashing Parameters
    ARGON2_TIME_COST: int = 2
    ARGON2_MEMORY_COST: int = 65536  # 64 MB
    ARGON2_PARALLELISM: int = 2

    # Network / HTTP
    CORS_ORIGIN: str = "*"
    LOG_LEVEL: Literal["debug", "info", "warn", "warning", "error"] = "info"

    # Storage & Upload Limits
    STORAGE_DIR: str = "storage/documents"
    MAX_UPLOAD_SIZE_BYTES: int = 20 * 1024 * 1024  # 20 MB

    # AI & Retrieval
    EMBEDDING_PROVIDER: Literal["fake", "none"] = "fake"
    AI_PROVIDER: Literal["fake", "extractive"] = "fake"
    CHUNK_SIZE: int = Field(default=500, ge=50, le=4000)
    CHUNK_OVERLAP: int = Field(default=50, ge=0, le=1000)
    SEARCH_DEFAULT_LIMIT: int = Field(default=10, ge=1, le=100)
    EVIDENCE_MIN_SIMILARITY: float = Field(default=0.15, ge=0.0, le=1.0)

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, v: str | None) -> str:
        """Convert standard postgresql:// connection strings to postgresql+asyncpg://."""
        if not v:
            return "postgresql+asyncpg://postgres:secret@localhost:5432/askbase"
        if v.startswith("postgres://"):
            return "postgresql+asyncpg://" + v[len("postgres://") :]
        if v.startswith("postgresql://") and not v.startswith("postgresql+asyncpg://"):
            return "postgresql+asyncpg://" + v[len("postgresql://") :]
        return v

    @model_validator(mode="after")
    def validate_secrets(self) -> "Settings":
        """Validate JWT secret strictness according to active environment."""
        if self.ENVIRONMENT == "production":
            if not self.JWT_SECRET or len(self.JWT_SECRET.strip()) < 32:
                raise ValueError("JWT_SECRET must be at least 32 characters in production mode.")
            if self.JWT_SECRET == DEVELOPMENT_JWT_SECRET:
                raise ValueError("Cannot use development JWT placeholder in production mode.")
        else:
            if not self.JWT_SECRET or not self.JWT_SECRET.strip():
                self.JWT_SECRET = DEVELOPMENT_JWT_SECRET
            elif len(self.JWT_SECRET.strip()) < 16:
                raise ValueError("JWT_SECRET must be at least 16 characters in non-production.")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load and cache validated application settings."""
    return Settings()


def reset_settings() -> None:
    """Clear cached settings (useful for isolated configuration testing)."""
    get_settings.cache_clear()
