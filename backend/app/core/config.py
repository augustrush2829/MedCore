from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./medcore_dev.db"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    cors_origins: str = "http://localhost:3000"
    environment: Literal["development", "production"] = "development"
    patient_upload_dir: str = "storage/patient_uploads"
    tesseract_languages: str = "eng+mon"
    rag_top_k: int = 6
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b-instruct"
    ollama_vision_model: str = "qwen2.5vl:7b"
    embedding_model_name: str = "intfloat/multilingual-e5-base"
    login_rate_limit_max_attempts: int = 5
    login_rate_limit_window_seconds: int = 900
    login_rate_limit_lockout_seconds: int = 900
    redis_url: str | None = None
    s3_endpoint_url: str | None = None
    s3_bucket: str = "medcore-patient-uploads"
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    s3_region: str = "us-east-1"
    s3_presigned_url_expire_seconds: int = 300

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode="after")
    def _require_postgres_outside_development(self) -> "Settings":
        if self.environment == "development":
            return self
        if self.database_url.startswith("sqlite"):
            raise ValueError(
                f"DATABASE_URL must be set to a Postgres connection string when "
                f"ENVIRONMENT={self.environment!r} (sqlite is a development-only fallback). "
                "Set DATABASE_URL to e.g. postgresql+psycopg://user:pass@host:5432/dbname."
            )
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
