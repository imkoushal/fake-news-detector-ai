"""
FastAPI REST API for fake news detection
Run with: uvicorn api:app --reload
Install dependencies: pip install fastapi uvicorn slowapi
"""
try:
    from fastapi import FastAPI, HTTPException, Depends, Header, Request
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    from typing import Optional, List
    import joblib
    import re
    from datetime import datetime
    import hashlib
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    print("FastAPI not installed. Install with: pip install fastapi uvicorn slowapi pydantic")
    print("This file is optional and not required for the main application.")

if not FASTAPI_AVAILABLE:
    # Create dummy app to prevent errors
    class DummyApp:
        pass
    app = DummyApp()
else:
    # Initialize FastAPI
    app = FastAPI(
        title="Fake News Detector API",
        description="Hybrid ML-powered fake news detection API",
        version="2.0"
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rate limiting
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # API Key management (simple version)
    API_KEYS = {
        "demo_key_123": "demo_user",
        "prod_key_456": "production_user"
    }

    def verify_api_key(x_api_key: str = Header(None)):
        """Verify API key"""
        if x_api_key not in API_KEYS:
            raise HTTPException(status_code=401, detail="Invalid API key")
        return API_KEYS[x_api_key]

    # Load model
    try:
        model = joblib.load('models/model.joblib')
        tfidf = joblib.load('models/tfidf.joblib')
        MODEL_LOADED = True
    except:
        MODEL_LOADED = False

    # Request/Response models
    class Article(BaseModel):
        text: str
        url: Optional[str] = None
        source: Optional[str] = None

    class PredictionResponse(BaseModel):
        prediction: str
        confidence: float
        real_probability: float
        fake_probability: float
        red_flag_score: float
        category: Optional[str] = None
        timestamp: str
        model_version: str = "2.0_advanced"

    class BatchArticle(BaseModel):
        id: str
        text: str

    class BatchRequest(BaseModel):
        articles: List[BatchArticle]

    # Helper functions
    def clean_text(text: str) -> str:
        """Clean and preprocess text"""
        text = str(text).lower()
        text = re.sub(r'http\\S+|www\\S+|https\\S+', '', text)
        text = re.sub(r'\\S+@\\S+', '', text)
        text = re.sub(r'[^a-zA-Z0-9\\s]', ' ', text)
        text = re.sub(r'\\s+', ' ', text)
        text = ' '.join([word for word in text.split() if len(word) > 2])
        return text.strip()

    def detect_red_flags(text: str) -> float:
        """Detect fake news red flags"""
        red_flags = 0
        max_flags = 10
        
        text_lower = text.lower()
        
        # Check for conspiracy keywords
        conspiracy_words = ['big pharma', 'mainstream media', 'deep state', 'government coverup']
        if any(word in text_lower for word in conspiracy_words):
            red_flags += 2
        
        # Check for medical misinformation
        medical_fraud = ['doctors dont want you to know', 'miracle cure', 'ancient remedy']
        if any(phrase in text_lower for phrase in medical_fraud):
            red_flags += 3
        
        # Check for urgency manipulation
        urgency = ['share before deleted', 'share now', 'censored']
        if any(word in text_lower for word in urgency):
            red_flags += 2
        
        # Check for excessive caps
        caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
        if caps_ratio > 0.1:
            red_flags += 1
        
        # Check for excessive punctuation
        if text.count('!') > 5 or text.count('?') > 5:
            red_flags += 1
        
        return min(red_flags, max_flags) / max_flags

    # API Endpoints
    @app.get("/")
    async def root():
        """API root endpoint"""
        return {
            "name": "Fake News Detector API",
            "version": "2.0",
            "status": "operational" if MODEL_LOADED else "model_not_loaded",
            "endpoints": {
                "analyze": "/api/v1/analyze",
                "batch": "/api/v1/batch",
                "health": "/health"
            }
        }

    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy" if MODEL_LOADED else "unhealthy",
            "model_loaded": MODEL_LOADED,
            "timestamp": datetime.now().isoformat()
        }

    @app.post("/api/v1/analyze", response_model=PredictionResponse)
    @limiter.limit("30/minute")
    async def analyze_article(
        article: Article,
        request: Request,
        user: str = Depends(verify_api_key)
    ):
        """Analyze single article for fake news"""
        if not MODEL_LOADED:
            raise HTTPException(status_code=503, detail="Model not loaded")
        
        if len(article.text) < 100:
            raise HTTPException(status_code=400, detail="Article text too short (minimum 100 characters)")
        
        # Clean text
        cleaned = clean_text(article.text)
        
        # Get prediction
        features = tfidf.transform([cleaned])
        proba = model.predict_proba(features)[0]
        
        real_prob = float(proba[0])
        fake_prob = float(proba[1])
        
        # Detect red flags
        red_flag_score = detect_red_flags(article.text)
        
        # Determine prediction
        prediction = "FAKE" if fake_prob > 0.5 else "REAL"
        confidence = max(real_prob, fake_prob) * 100
        
        return PredictionResponse(
            prediction=prediction,
            confidence=confidence,
            real_probability=real_prob,
            fake_probability=fake_prob,
            red_flag_score=red_flag_score,
            category=None,
            timestamp=datetime.now().isoformat()
        )

    @app.post("/api/v1/batch")
    @limiter.limit("10/minute")
    async def analyze_batch(
        request: Request,
        batch: BatchRequest,
        user: str = Depends(verify_api_key)
    ):
        """Analyze multiple articles in batch"""
        if not MODEL_LOADED:
            raise HTTPException(status_code=503, detail="Model not loaded")
        
        if len(batch.articles) > 50:
            raise HTTPException(status_code=400, detail="Maximum 50 articles per batch")
        
        results = []
        
        for article in batch.articles:
            try:
                cleaned = clean_text(article.text)
                features = tfidf.transform([cleaned])
                proba = model.predict_proba(features)[0]
                
                real_prob = float(proba[0])
                fake_prob = float(proba[1])
                red_flag_score = detect_red_flags(article.text)
                
                prediction = "FAKE" if fake_prob > 0.5 else "REAL"
                confidence = max(real_prob, fake_prob) * 100
                
                results.append({
                    "id": article.id,
                    "prediction": prediction,
                    "confidence": confidence,
                    "real_probability": real_prob,
                    "fake_probability": fake_prob,
                    "red_flag_score": red_flag_score
                })
            except Exception as e:
                results.append({
                    "id": article.id,
                    "error": str(e)
                })
        
        return {
            "total": len(batch.articles),
            "processed": len(results),
            "results": results,
            "timestamp": datetime.now().isoformat()
        }

    @app.get("/api/v1/stats")
    async def get_stats(user: str = Depends(verify_api_key)):
        """Get API usage statistics"""
        # In production, this would query a database
        return {
            "user": user,
            "total_requests": 0,
            "requests_today": 0,
            "avg_response_time": 0,
            "message": "Statistics tracking not yet implemented"
        }

if __name__ == "__main__":
    if FASTAPI_AVAILABLE:
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)
    else:
        print("FastAPI not installed. Please install with: pip install fastapi uvicorn slowapi pydantic")
