<![CDATA[# 🔍 Fake News Detector AI

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.48-FF4B4B.svg)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Accuracy](https://img.shields.io/badge/Accuracy-96.46%25-brightgreen.svg)](#model-performance)

A hybrid ML-powered fake news detection system combining a **5-model ensemble classifier** (96.46% accuracy), **Google Gemini AI** analysis, and **GNews API** verification — served via both a Streamlit dashboard and a FastAPI REST API.

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Model Performance](#model-performance)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Features

| Layer | Description |
|-------|-------------|
| **ML Ensemble** | 5 classifiers (LR, SGD, SVM, RF, GBM) with soft voting on 8 000 TF-IDF features |
| **Gemini AI** | 7-factor credibility analysis via Google Gemini 2.0 Flash |
| **GNews Verification** | Real-time cross-referencing against 19 trusted outlets |
| **Red Flag Engine** | Pattern-based detection of conspiracy, clickbait, medical misinformation |
| **REST API** | FastAPI with auth, rate limiting, batch processing, OpenAPI docs |
| **Web Dashboard** | Streamlit UI with dark mode, history, explainable AI, feedback system |
| **Database** | SQLite storage for analysis history, statistics, and user feedback |

---

## Architecture

```
Article Input
    │
    ├── ML Model (50%)  ──► 5-Model Ensemble ──► Soft Voting
    ├── Gemini AI (30%) ──► 7-Factor Analysis
    └── GNews API (20%) ──► Source Cross-Ref
    │
    ▼
FINAL VERDICT + Confidence Score + Red Flag Report
```

---

## Model Performance

| Metric | Score |
|--------|-------|
| **Accuracy** | **96.46%** |
| Precision | 95.84% |
| Recall | 97.14% |
| F1-Score | 96.48% |
| Validation | 97.10% |

**Training data:** 59,220 balanced articles from 4 datasets (ISOT, WELFake, Kaggle, fake_or_real_news) totalling 157,783 articles.

---

## Quick Start

### Prerequisites

- Python 3.10+
- ~500 MB disk space

### 1. Clone & Setup

```powershell
git clone https://github.com/imkoushal/fake-news-detector-ai.git
cd fake-news-detector-ai
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Configure Environment

```powershell
Copy-Item .env.example .env
# Edit .env and add your API keys:
#   GEMINI_API_KEY=your_key   → https://ai.google.dev/
#   GNEWS_API_KEY=your_key    → https://gnews.io/
```

### 3. Run

```powershell
# Streamlit Dashboard
streamlit run app.py
# → http://localhost:8501

# FastAPI REST API (separate terminal)
uvicorn api:app --reload
# → http://localhost:8000/docs
```

### 4. Retrain Model (optional)

```powershell
python train.py
```

---

## API Reference

### Endpoints

| Method | Endpoint | Auth | Rate Limit | Description |
|--------|----------|------|------------|-------------|
| `GET` | `/` | — | — | API status |
| `GET` | `/health` | — | — | Health check |
| `GET` | `/api/v1/status` | — | — | Detailed status with memory/CPU |
| `POST` | `/api/v1/analyze` | API Key | 30/min | Analyze single article |
| `POST` | `/api/v1/batch` | API Key | 10/min | Batch analyze (≤50 articles) |
| `GET` | `/api/v1/stats` | API Key | — | Usage statistics |

### Example Request

```powershell
# Analyze a single article
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/analyze" `
  -Method POST `
  -Headers @{"X-API-Key"="demo_key_123"; "Content-Type"="application/json"} `
  -Body '{"text":"Your full article text here (min 100 chars)..."}'
```

### Response Schema

```json
{
  "prediction": "FAKE",
  "confidence": 92.5,
  "real_probability": 0.075,
  "fake_probability": 0.925,
  "red_flag_score": 0.4,
  "category": null,
  "timestamp": "2026-03-23T16:30:00",
  "model_version": "2.0_advanced"
}
```

---

## Project Structure

```
fake-news-detector-ai/
├── app.py                   # Streamlit web dashboard (4 tabs)
├── api.py                   # FastAPI REST API server
├── train.py                 # Model training pipeline
├── database.py              # SQLite integration
├── enhanced_features.py     # Source analysis, topic classification
├── ui_components.py         # Streamlit UI components
├── state_management.py      # Session state management
├── api_client.py            # External API client (Gemini, GNews)
├── model_versioning.py      # Model version management
├── ultra_detector.py        # Advanced detection utilities
├── validate_config.py       # Configuration validation
├── requirements.txt         # Python dependencies
├── .env.example             # Environment variable template
├── .gitignore               # Git ignore rules
├── app_pages/               # Streamlit page modules
│   ├── analyze_page.py
│   ├── batch_page.py
│   └── dashboard_page.py
├── models/                  # Trained model artifacts
│   ├── model.joblib         # Ensemble classifier
│   ├── tfidf.joblib         # TF-IDF vectorizer
│   └── config.json          # Model metadata
├── data/                    # Training datasets (CSV, gitignored)
├── logs/                    # Training logs and plots
└── assets/                  # Static assets
```

---

## Configuration

### Environment Variables (`.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | — | Google Gemini API key |
| `GNEWS_API_KEY` | — | GNews API key |
| `MODEL_VERSION` | `2.0_advanced` | Model version identifier |
| `API_HOST` | `0.0.0.0` | API server host |
| `API_PORT` | `8000` | API server port |
| `DATABASE_PATH` | `analysis_history.db` | SQLite database path |

### API Keys

| Service | Free Tier | Get Key |
|---------|-----------|---------|
| Gemini | 15 req/min, 1,500 req/day | [ai.google.dev](https://ai.google.dev/) |
| GNews | 100 req/day | [gnews.io](https://gnews.io/) |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Model not loading | Ensure `models/model.joblib` & `models/tfidf.joblib` exist |
| Low confidence | Use full articles (500+ chars), not headlines |
| Import errors | Activate venv: `.venv\Scripts\Activate.ps1` |
| API 401 error | Pass `X-API-Key: demo_key_123` header |
| Streamlit won't start | Run: `.venv\Scripts\python.exe -m streamlit run app.py` |

---

## License

MIT © [imkoushal](https://github.com/imkoushal)
]]>
