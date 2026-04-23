from typing import Literal, Any
from pydantic import BaseModel, Field


class Entity(BaseModel):
    type: str
    value: str
    confidence: int = Field(default=80, ge=0, le=100)


class Sentiment(BaseModel):
    label: Literal["positive", "neutral", "negative"] = "neutral"
    score: float = Field(default=0.5, ge=0.0, le=1.0)


class ScanResult(BaseModel):
    filename: str
    file_type: str
    file_size_mb: float
    media_type: str
    preview_base64: str
    document_type: str = "Unknown"
    language: str = "English"
    summary: str = ""
    full_text: str = ""
    entities: list[Entity] = Field(default_factory=list)
    key_values: dict[str, str] = Field(default_factory=dict)
    tables: list[list[list[str]]] = Field(default_factory=list)
    sentiment: Sentiment = Field(default_factory=Sentiment)
    quality_score: int = Field(default=0, ge=0, le=100)
    confidence: int = Field(default=0, ge=0, le=100)
    raw_model_output: str = ""


class ScanResponse(BaseModel):
    job_id: str
    result: ScanResult


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    question: str
    answer: str


class ApiError(BaseModel):
    error: str
    details: dict[str, Any] | None = None
