<![CDATA[# 📰 Fake News Detection API

An AI-powered backend system that classifies news articles as **REAL or FAKE** using a machine learning pipeline built with FastAPI.

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-1.5-F7931E?logo=scikit-learn&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 🚀 Features

- 🔍 Detects fake vs real news from text input
- ⚡ FastAPI-based REST API with auto-generated docs
- 🧠 ML pipeline (TF-IDF + ensemble classifier) — **96.46% accuracy**
- 📊 Confidence score & probability breakdown per prediction
- 🚩 Red flag detection (clickbait, conspiracy, medical misinformation)
- 🔐 API key authentication & rate limiting
- 📦 Batch analysis (up to 50 articles per request)
- 🧩 Modular and clean architecture
- 🔗 CORS-enabled — ready for frontend integration

---

## 🧠 Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | FastAPI, Uvicorn |
| **ML Model** | Scikit-learn (Ensemble Classifier) |
| **NLP** | TF-IDF Vectorization (8 000 features, trigrams) |
| **Serialization** | Joblib |
| **Language** | Python 3.10+ |

---

## 📂 Project Structure

```
fake-news-detector-ai/
├── api.py                # FastAPI REST API server
├── train.py              # Model training pipeline
├── app.py                # Streamlit web dashboard
├── database.py           # SQLite integration
├── enhanced_features.py  # Source analysis, topic classification
├── api_client.py         # External API client (Gemini, GNews)
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variable template
├── .gitignore
├── app_pages/            # Streamlit page modules
├── models/               # Trained model artifacts
│   ├── model.joblib      # Ensemble classifier
│   ├── tfidf.joblib      # TF-IDF vectorizer
│   └── config.json       # Model metadata
└── data/                 # Training datasets (gitignored)
```

---

## ⚡ Quick Start

```bash
# 1. Clone
git clone https://github.com/imkoushal/fake-news-detector-ai.git
cd fake-news-detector-ai

# 2. Setup
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows
pip install -r requirements.txt

# 3. Configure
copy .env.example .env              # Add your API keys

# 4. Run API
uvicorn api:app --reload
# → http://localhost:8000/docs
```

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | API info |
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/analyze` | Analyze single article |
| `POST` | `/api/v1/batch` | Batch analyze (≤ 50) |
| `GET` | `/api/v1/stats` | Usage statistics |

### Example Request

```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "X-API-Key: demo_key_123" \
  -H "Content-Type: application/json" \
  -d '{"text": "Your full article text here..."}'
```

### Example Response

```json
{
  "prediction": "FAKE",
  "confidence": 92.5,
  "real_probability": 0.075,
  "fake_probability": 0.925,
  "red_flag_score": 0.4,
  "text_length": 1250,
  "timestamp": "2026-03-23T17:00:00",
  "model_version": "2.1.0"
}
```

---

## 📊 Model Performance

| Metric | Score |
|--------|-------|
| **Accuracy** | **96.46%** |
| Precision | 95.84% |
| Recall | 97.14% |
| F1-Score | 96.48% |

> Trained on **59,220 balanced articles** from 4 datasets (ISOT, WELFake, Kaggle, fake_or_real_news).

---

## ⚙️ Configuration

Create a `.env` file from the template:

```
GEMINI_API_KEY=your_key_here
GNEWS_API_KEY=your_key_here
```

| Service | Free Tier | Get Key |
|---------|-----------|---------|
| Google Gemini | 15 req/min | [ai.google.dev](https://ai.google.dev/) |
| GNews | 100 req/day | [gnews.io](https://gnews.io/) |

---

## 🛠️ Troubleshooting

| Issue | Fix |
|-------|-----|
| Model not loading | Ensure `models/model.joblib` & `models/tfidf.joblib` exist |
| Low confidence | Use full articles (500+ chars), not headlines |
| Import errors | Activate venv first |
| API 401 | Include header `X-API-Key: demo_key_123` |

---

## 📝 License

MIT © [imkoushal](https://github.com/imkoushal)
]]>
