import os
from functools import lru_cache
from pydantic import BaseModel, Field


class Settings(BaseModel):
    gemini_api_key: str = Field(default="")
    allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    max_file_size_mb: int = 10
    max_image_dimension: int = 1600
    model_name: str = "gemini-1.5-flash"
    request_timeout_seconds: int = 120


@lru_cache
def get_settings() -> Settings:
    raw_origins = os.getenv("VISIO_ALLOWED_ORIGINS", "http://localhost:3000")
    origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
    return Settings(
        gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
        allowed_origins=origins,
        max_file_size_mb=int(os.getenv("VISIO_MAX_FILE_SIZE_MB", "10")),
        max_image_dimension=int(os.getenv("VISIO_MAX_IMAGE_DIMENSION", "1600")),
        model_name=os.getenv("VISIO_MODEL", "gemini-1.5-flash"),
        request_timeout_seconds=int(os.getenv("VISIO_REQUEST_TIMEOUT_SECONDS", "120")),
    )
