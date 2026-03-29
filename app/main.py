from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.core import analyze_article   
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Fake News Detection API", version="1.0")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
class AnalyzeRequest(BaseModel):
    text: str

@app.get("/")
def home():
    return {"message": "Server working"}

@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    try:
        result = analyze_article(request.text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))