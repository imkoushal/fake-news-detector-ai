"""
Pydantic schemas for API request/response validation.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ArticleRequest(BaseModel):
    text: str = Field(..., min_length=100, max_length=50000, description="Article text to analyze")
    url: Optional[str] = Field(None, description="Source URL of the article")
    source: Optional[str] = Field(None, description="Source name")


class PredictionResponse(BaseModel):
    prediction: str
    confidence: float
    real_probability: float
    fake_probability: float
    red_flag_score: float
    ood_warning: Optional[str] = None
    category: Optional[str] = None
    model_version: str = "3.0"
    timestamp: str
    request_id: str


class BatchArticle(BaseModel):
    id: str
    text: str = Field(..., min_length=50)


class BatchRequest(BaseModel):
    articles: List[BatchArticle] = Field(..., max_length=50)


class BatchResultItem(BaseModel):
    id: str
    prediction: Optional[str] = None
    confidence: Optional[float] = None
    real_probability: Optional[float] = None
    fake_probability: Optional[float] = None
    red_flag_score: Optional[float] = None
    error: Optional[str] = None


class BatchResponse(BaseModel):
    total: int
    processed: int
    succeeded: int
    failed: int
    results: List[BatchResultItem]
    timestamp: str
    request_id: str


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_version: str
    database_connected: bool
    gemini_available: bool
    gnews_configured: bool
    uptime_seconds: float
    timestamp: str


class StatsResponse(BaseModel):
    user: str
    total_predictions: int
    predictions_by_type: dict
    avg_confidence: float
    avg_latency_ms: float
    error_rate: float
    uptime_seconds: float
