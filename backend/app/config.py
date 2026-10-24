from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional
import os

class Settings(BaseSettings):
    ENVIRONMENT: str = Field(default="development")
    LOG_LEVEL: str = Field(default="INFO")
    PORT: int = Field(default=8000)
    HOST: str = Field(default="0.0.0.0")

    # Databases
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@postgres:5432/incubrix_broll"
    )
    DATABASE_URL_SYNC: str = Field(
        default="postgresql://postgres:postgres@postgres:5432/incubrix_broll"
    )

    # Redis & Celery
    REDIS_URL: str = Field(default="redis://redis:6379/0")
    CELERY_BROKER_URL: str = Field(default="redis://redis:6379/0")
    CELERY_RESULT_BACKEND: str = Field(default="redis://redis:6379/1")

    # MinIO / Object Storage
    MINIO_ENDPOINT: str = Field(default="minio:9000")
    MINIO_ROOT_USER: str = Field(default="minioadmin")
    MINIO_ROOT_PASSWORD: str = Field(default="minioadmin")
    MINIO_BUCKET_NAME: str = Field(default="incubrix-media")
    MINIO_USE_SSL: bool = Field(default=False)
    MINIO_PUBLIC_ENDPOINT: str = Field(default="http://localhost:9000")
    STORAGE_PUBLIC_URL: str = Field(default=os.environ.get("STORAGE_PUBLIC_URL", "http://localhost:8000"))

    # Adapters (mock | real)
    STT_ADAPTER: str = Field(default="mock")
    TTS_ADAPTER: str = Field(default="mock")
    LLM_ADAPTER: str = Field(default="mock")
    FOOTAGE_ADAPTER: str = Field(default="mock")
    VISION_ADAPTER: str = Field(default="mock")

    # External APIs and Providers
    FOOTAGE_PROVIDERS: str = Field(default="pixabay,pexels,mock")
    SETTINGS_VERSION: str = Field(default="1.0.0")
    PEXELS_API_KEY: Optional[str] = Field(default=None)
    PIXABAY_API_KEY: Optional[str] = Field(default=None)
    OPENAI_API_KEY: Optional[str] = Field(default=None)

    # Secrets
    CALLBACK_SECRET: str = Field(default="incubrix_secret_dev_key_2026_super_secure")

    # Pipeline Rules
    MIN_SCENE_DURATION_SECONDS: float = Field(default=2.5)
    STOCK_SELECTION_THRESHOLD: float = Field(default=0.28)
    MAX_AUDIO_DURATION_SECONDS: int = Field(default=600)
    CACHE_DIR: str = Field(default="/tmp/incubrix_cache")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
