from pydantic import BaseModel, Field

class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=5000)

class AnalyzeResponse(BaseModel):
    prediction: str
    confidence: float
    ml_score: float
    ai_score: float
    web_score: float