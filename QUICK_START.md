# Quick Start Guide - Environment Setup

## 📋 Quick Setup (5 minutes)

### 1. Copy Environment File
```bash
cp .env.example .env
```

### 2. Update `.env` with Your API Keys
Edit `.env` and add:
```
GEMINI_API_KEY=your_actual_key_here
GNEWS_API_KEY=your_actual_key_here
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 4. Run Application
```bash
streamlit run app.py
```

---

## 🔐 **Security Best Practices**

### ✅ DO:
- Keep `.env` file **PRIVATE** (never commit to git)
- Use different API keys for dev/prod environments
- Rotate API keys regularly
- Use strong, unique API keys

### ❌ DON'T:
- Hardcode API keys in code
- Share `.env` file with others
- Commit `.env` to version control
- Use development keys in production

---

## 🌐 API Keys Setup

### Getting Gemini API Key
1. Go to https://ai.google.dev/
2. Click "Get API Key" → Create new API key
3. Copy and paste into `.env` as `GEMINI_API_KEY`

### Getting GNews API Key
1. Visit https://gnews.io/
2. Sign up for free tier
3. Copy and paste into `.env` as `GNEWS_API_KEY`

---

## 📝 Environment Variables Reference

| Variable | Purpose | Required | Default |
|----------|---------|----------|---------|
| `GEMINI_API_KEY` | Google AI API for credibility analysis | Yes | - |
| `GNEWS_API_KEY` | News search API | Yes | - |
| `MODEL_PATH` | Path to ML model | No | models/pipeline.joblib |
| `TFIDF_PATH` | Path to TF-IDF vectorizer | No | models/tfidf.joblib |
| `CONFIG_PATH` | Model config file | No | models/config.json |
| `MODEL_VERSION` | Current model version | No | 2.0_advanced |
| `DATABASE_PATH` | SQLite database location | No | analysis_history.db |
| `API_HOST` | API server host | No | 0.0.0.0 |
| `API_PORT` | API server port | No | 8000 |
| `ENV` | Environment (development/production) | No | development |
| `DEBUG` | Enable debug mode | No | true |

---

## 🚀 Running Different Components

### Web App (Streamlit)
```bash
streamlit run app.py
# Access at http://localhost:8501
```

### REST API (FastAPI)
```bash
python api.py
# Docs at http://localhost:8000/docs
# Health check: http://localhost:8000/health
```

### Model Training
```bash
python train.py
# Trains new ensemble model, saves to models/
```

### Development Mode
```bash
pip install -r requirements-dev.txt
# Run with pytest, debugging tools, etc.
```

---

## ✅ Input Validation

The application now validates all user inputs:

### Text Input Rules
- **Minimum length**: 10 characters
- **Maximum length**: 5000 characters
- **Format**: Must be plain text

### Batch Upload Rules
- **Max articles**: 50 per batch
- **Min articles**: 1 per batch
- **Text per article**: 10-5000 characters
- **ID per article**: Required, max 100 chars

### API Endpoints
- All endpoints validate inputs using Pydantic
- Invalid inputs return helpful error messages
- Rate limiting enabled: 30 req/min single, 10 req/min batch

---

## 📊 Model Versioning

Track different model versions:

```python
from model_versioning import get_model_manager

manager = get_model_manager()

# Register a new model
manager.register_model(
    version="2.1_experimental",
    model_path="models/model_v2.1.joblib",
    metadata={"accuracy": 0.967, "author": "Your Name"}
)

# Activate a model
manager.set_active_model("2.1_experimental")

# Get current active model
active = manager.get_active_model()
print(f"Active: {active['version']}")

# View history
for entry in manager.get_history():
    print(entry)
```

---

## 🏥 Health Checks

### Quick Health Check
```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-03-21T10:30:00",
  "version": "2.0"
}
```

### Detailed Status
```bash
curl http://localhost:8000/api/v1/status
```

**Response:**
```json
{
  "status": "operational",
  "model_loaded": true,
  "version": "2.0_advanced",
  "memory_usage_mb": 256.5,
  "cpu_percent": 15.2
}
```

---

## 🧪 Testing API

### Example Single Article Analysis
```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: demo_key_123" \
  -d '{"text": "This is a test article with enough content to be processed by the system"}'
```

### Example Batch Analysis
```bash
curl -X POST http://localhost:8000/api/v1/batch \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: demo_key_123" \
  -d '{
    "articles": [
      {"id": "1", "text": "First article text here with minimum length..."},
      {"id": "2", "text": "Second article text here with minimum length..."}
    ]
  }'
```

---

## 🐛 Troubleshooting

### API Keys Not Working
1. Check `.env` file exists in project root
2. Verify keys are correct (no extra spaces)
3. Restart application after updating `.env`
4. Check `.env` is readable by your user

### Model Not Loading
1. Ensure `models/pipeline.joblib` exists
2. Check `MODEL_PATH` in `.env`
3. Verify file isn't corrupted: `python -c "import joblib; joblib.load('models/pipeline.joblib')"`

### Port Already in Use
```bash
# For FastAPI (8000)
python api.py --port 8001

# For Streamlit (8501)
streamlit run app.py --server.port 8502
```

### Database Locked
```bash
# Delete old database and let app recreate
rm analysis_history.db
```

---

## 📚 Further Reading

- See `PROJECT_SUMMARY.md` for architecture details
- See `README.md` for full feature documentation
- Check `requirements-dev.txt` for development tools
