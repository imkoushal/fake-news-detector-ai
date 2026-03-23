from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import joblib
import numpy as np
from typing import Any, Dict
from utils import clean_text   

app = FastAPI()

class AnalyzeRequest(BaseModel):
    text: str

class AnalyzeResponse(BaseModel):
    prediction: str
    confidence: float

# Load model at startup
@app.on_event("startup")
def load_model():
    global pipeline
    pipeline = joblib.load("models/pipeline_svm.joblib")

@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}

@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest):
    if "pipeline" not in globals():
        raise HTTPException(status_code=500, detail="Model not loaded.")

    text = request.text

    # Prediction
    pred = pipeline.predict([text])[0]

    # Convert to label
    label = "FAKE" if pred == 1 else "REAL"

    # Confidence
    if hasattr(pipeline, "predict_proba"):
        proba = pipeline.predict_proba([text])[0]
        confidence = float(np.max(proba))
    else:
        confidence = 1.0

    return AnalyzeResponse(prediction=label, confidence=confidence)