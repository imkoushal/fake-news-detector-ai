<p align="center">
  <img src="landing-page/public/favicon.svg" alt="VerifAI Logo" width="80" />
</p>

<h1 align="center">🔍 Fake News Detector AI</h1>

<p align="center">
  <strong>A production-hardened, multi-layered misinformation detection system combining a high-accuracy ML ensemble with a RAG pipeline for real-time, evidence-based news verification.</strong>
</p>

<p align="center">
  <a href="https://fake-news-detector-8djq.onrender.com"><img src="https://img.shields.io/badge/🌐_Live_Demo-Try_it_now-6c5ce7?style=for-the-badge" alt="Live Demo" /></a>
  <a href="#license"><img src="https://img.shields.io/badge/License-Attribution_Required-ff6b6b?style=for-the-badge" alt="License" /></a>
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React" />
</p>

<p align="center">
  <a href="https://fake-news-detector-8djq.onrender.com">🌐 Live App</a> •
  <a href="#key-features">✨ Features</a> •
  <a href="#architecture">🏗️ Architecture</a> •
  <a href="#installation">🚀 Setup</a> •
  <a href="#api-endpoints">🔌 API</a> •
  <a href="#license">📄 License</a>
</p>

---

## 📖 Overview

The **Fake News Detector AI** tackles misinformation from two complementary angles:

1. **Linguistic Analysis (ML):** A 5-model Voting Ensemble trained on 100,000+ articles detects the *writing style* of fake news — sensationalism, conspiracy language, clickbait patterns, and structural anomalies.
2. **Factual Verification (RAG):** A Retrieval-Augmented Generation pipeline queries live news via GNews, injects the results into a Groq LLM prompt, and cross-references the article's claims against real-time evidence.

This dual approach catches both *stylistically* fake articles (clickbait, conspiracy blogs) and *factually* fake articles (fabricated events, outdated claims presented as new).

> **🌐 Try it live:** [fake-news-detector-8djq.onrender.com](https://fake-news-detector-8djq.onrender.com)

---

## ✨ Key Features

### 🧠 RAG-Powered Real-Time Verification
- Extracts keywords from user input and queries the **GNews API** for live headlines
- Injects live news context directly into the **Groq LLM** prompt
- Cross-references article claims against breaking news evidence
- **Intelligent Fallback:** Automatically switches to standalone style-analysis mode if no live news is found

### 🌐 Multi-Source Intelligence & Caching
- **Google Fact Check API:** Queries Google's ClaimReview database covering 200+ fact-checking orgs (Reuters, AFP, Alt News, etc.)
- **Google Safe Browsing API:** Extracts URLs from article text and scans for malware, phishing, and social engineering
- **Source Credibility Database:** Built-in domain reputation system covering 80+ Indian and international news sources
- **Claim Caching Engine:** In-memory TTL cache with normalized hashing — **160x speedup** on repeated viral claims

### 🎓 Advanced Features
- **Educator Mode:** Step-by-step pipeline transparency showing exactly how each analysis step reached its conclusion
- **Voice Input (Groq Whisper):** Upload audio files or record directly from the browser — supports Hindi, English, 50+ languages
- **India Threat Scanner:** 9-category detection engine with 150+ India-specific keywords covering UPI fraud, fake schemes, WhatsApp forward patterns, health misinfo, and more
- **Community Dashboard:** Live platform-wide stats bar showing total analyses, fake detection rate, and average confidence

### 🤖 5-Model Voting Ensemble
| Model | Type | Key Config |
|-------|------|------------|
| Logistic Regression | Linear | RandomizedSearchCV tuned, C=6.80 |
| Random Forest | Tree-based | 100 estimators, max_depth=15 |
| SGD Classifier | Linear | Modified Huber loss |
| LinearSVC | Linear | Calibrated via sigmoid method |
| LightGBM | Gradient Boosted | 200 estimators, 80 leaves |

### 🧬 Hybrid Feature Engineering
- **TF-IDF Vectorization:** 25,000 n-gram features (unigrams to trigrams) with sublinear TF scaling
- **20 Custom Meta-Features:** `all_caps_ratio`, `conspiracy_score`, `sensationalism_score`, `flesch_kincaid_grade`, `clickbait_score`, `has_attribution`, and more
- **NUM Token Masking:** Numbers normalized to `<NUM>` tokens during preprocessing to preserve sentence structure

### 🛡️ Production Hardened
- **SSRF Protection:** DNS resolution + private IP blocking on all external fetches
- **Async I/O:** All HTTP calls via `httpx.AsyncClient` with connection pooling
- **JWT Verification:** Google OAuth tokens cryptographically verified via `google-auth`
- **Error Sanitization:** Global exception handler — no raw tracebacks leak to clients
- **Request Correlation:** `X-Request-ID` middleware for end-to-end log tracing
- **Rate Limiting:** Per-IP rate limiting on all endpoints via SlowAPI
- **Path Traversal Protection:** `.resolve()` + prefix validation on SPA static serving
- **React ErrorBoundary:** Catches unhandled component crashes with recovery UI

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                   User Input (Article Text)          │
└──────────────────────────┬──────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
  ┌──────────────┐  ┌─────────────┐  ┌──────────────────┐
  │  ML Pipeline │  │ RAG Pipeline│  │ Threat Scanner   │
  │              │  │ (Smart      │  │                  │
  │ TF-IDF +    │  │  Verify)    │  │ • India Scams    │
  │ 20 Meta     │  │             │  │ • Safe Browsing  │
  │ Features    │  │ GNews ─►    │  │ • Source Cred.   │
  │      │      │  │ Groq LLM   │  │ • Fact Check API │
  │      ▼      │  │      │      │  └──────────────────┘
  │ 5-Model     │  │      ▼      │
  │ Ensemble    │  │ VERDICT +   │
  │      │      │  │ Evidence    │
  │      ▼      │  └─────────────┘
  │ REAL/FAKE   │
  │ + Confidence│
  └──────────────┘
```

### Backend Modules
| Module | Purpose |
|--------|---------|
| `backend/db.py` | PostgreSQL/SQLite connection pooling, `execute_db()` helper |
| `backend/auth.py` | Password hashing (bcrypt), session management, token auth |
| `backend/cache.py` | Thread-safe TTL-based LRU cache with `threading.Lock` |
| `backend/ssrf.py` | URL validation against private/internal IP ranges |
| `backend/http_client.py` | Shared `httpx.AsyncClient` with connection pooling |
| `backend/credibility_db.py` | Domain reputation database (80+ sources) |
| `backend/threat_patterns.py` | India-specific scam/misinfo pattern detection |

---

## 📈 Model Performance

### ML Ensemble (v6.0)

| Metric | Score |
|--------|-------|
| **Accuracy** | **94.77%** |
| Precision | 95.81% |
| Recall | 93.66% |
| F1-Score | 94.72% |
| ROC-AUC | 99.09% |

### Cross-Domain: WelFake Dataset (72K Articles)

| Metric | Score |
|--------|-------|
| Accuracy | 97.72% |
| ROC-AUC | 99.78% |
| High-Confidence (≥90%) Accuracy | 99.97% |

---

## 🚀 Installation

### Prerequisites
- Python 3.10+
- Node.js 18+ (for frontend build)
- At least 2GB RAM

### Setup
```bash
# Clone the repository
git clone https://github.com/imkoushal/fake-news-detector-ai.git
cd fake-news-detector-ai

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### Configure API Keys
Create a `.env` file (or copy `.env.example`):
```env
GROQ_API_KEY=your_groq_api_key       # https://console.groq.com/
GNEWS_API_KEY=your_gnews_api_key     # https://gnews.io/
GOOGLE_CLIENT_ID=your_client_id      # https://console.cloud.google.com/
```

### Run Locally
```bash
# Start the FastAPI backend (serves both API + frontend)
uvicorn api:app --port 8000

# Open http://localhost:8000
```

### Build Frontend (Optional)
```bash
cd landing-page
npm install
npm run build
```

---

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/analyze` | POST | ML-only prediction (fast, no API calls) |
| `/api/v1/smart-verify` | POST | **RAG pipeline** — GNews → Groq LLM verification |
| `/api/v1/fact-check` | POST | Google Fact Check API integration |
| `/api/v1/safe-browsing` | POST | URL threat detection via Google Safe Browsing |
| `/api/v1/source-credibility` | POST | Domain reputation scoring (80+ sources) |
| `/api/v1/india-threat-scan` | POST | India-specific scam/misinfo pattern detection |
| `/api/v1/transcribe` | POST | Audio transcription via Groq Whisper |
| `/api/v1/fetch-url` | POST | Extract article text from URL (SSRF-protected) |
| `/api/v1/batch` | POST | Batch analysis (up to 50 articles) |
| `/api/v1/community-stats` | GET | Platform-wide anonymized analysis stats |
| `/api/v1/health` | GET | Tiered health check (model, DB, cache, API keys) |
| `/api/v1/model-info` | GET | Current model version and metadata |

### Example: Smart Verify Request
```bash
curl -X POST https://fake-news-detector-8djq.onrender.com/api/v1/smart-verify \
  -H "Content-Type: application/json" \
  -d '{"text": "NASA confirms Earth will experience 15 days of darkness in November"}'
```

### Response
```json
{
  "verdict": "LIKELY_FALSE",
  "credibility": "LOW",
  "credibility_score": 0.2,
  "confidence": 92,
  "analysis": "This is a recurring internet hoax. No credible space agency has made such a claim...",
  "web": {
    "total_articles": 4,
    "trusted_count": 2,
    "articles": [...]
  }
}
```

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------| 
| **Backend** | FastAPI, Python 3.11 | Async REST API with rate limiting |
| **ML** | Scikit-Learn, LightGBM | 5-model voting ensemble |
| **NLP** | spaCy, TF-IDF | Text processing & feature extraction |
| **LLM** | Groq API | RAG-powered fact-checking |
| **HTTP** | httpx (async) | Non-blocking external API calls |
| **External APIs** | GNews, Google Fact Check, Safe Browsing | Live verification & threat detection |
| **Frontend** | React 18, TypeScript, Vite | Modern responsive SPA |
| **Auth** | bcrypt, Google OAuth (JWT verified) | Secure session management |
| **Database** | PostgreSQL (prod) / SQLite (dev) | Connection-pooled data layer |
| **Caching** | Thread-safe in-memory LRU | TTL-based claim deduplication |
| **Security** | SSRF protection, CORS whitelist, rate limiting | Production hardening |
| **Deployment** | Docker (multi-stage), Render | Containerized cloud deployment |

---

## 📁 Project Structure

```
fake-news-detector-ai/
├── api.py                          # FastAPI backend (2,100+ lines)
├── train.py                        # ML training pipeline
├── utils.py                        # NLP text cleaning & preprocessing
├── meta_features.py                # 20 custom linguistic feature extractors
├── enhanced_features.py            # Extended feature generation
├── ood_detector.py                 # Out-of-Distribution detection
│
├── backend/                        # Modular backend package
│   ├── db.py                       # PostgreSQL/SQLite connection pooling
│   ├── auth.py                     # Password hashing & session management
│   ├── cache.py                    # Thread-safe TTL-based LRU cache
│   ├── ssrf.py                     # SSRF protection module
│   ├── http_client.py              # Shared async HTTP client
│   ├── credibility_db.py           # Domain reputation database
│   └── threat_patterns.py          # India-specific threat scanner
│
├── landing-page/                   # React SPA frontend
│   ├── src/
│   │   ├── pages/                  # Analytics, Dashboard, History, etc.
│   │   ├── components/             # ErrorBoundary, Sidebar, Navbar, etc.
│   │   ├── context/                # AuthContext, ToastContext
│   │   └── lib/api.ts              # API client config
│   └── dist/                       # Production build
│
├── models/                         # Trained model artifacts
│   ├── model.joblib                # Voting ensemble
│   ├── tfidf.joblib                # TF-IDF vectorizer
│   ├── scaler.joblib               # Meta-feature scaler
│   └── config.json                 # Model metadata & threshold
│
├── tests/                          # Test suite
├── Dockerfile                      # Multi-stage Docker build
├── docker-compose.yml              # Multi-service orchestration
├── requirements.txt                # Development dependencies
├── requirements-deploy.txt         # Production dependencies
├── .env.example                    # Environment variable template
├── Procfile                        # Render deployment config
└── LICENSE                         # Attribution-Required License
```

---

## 📊 Evaluation & Monitoring

```bash
# Generate evaluation report
python eval_report.py --save

# WelFake cross-domain evaluation
python eval_welfake.py

# Run test suite
pytest tests/ -v

# Retrain the model
python train.py
```

---

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

**Important:** All contributions must comply with the [Attribution-Required License](LICENSE).

---

## 📄 License

This project is licensed under the **Attribution-Required License (ARL)**.

### What this means:
- ✅ You **can** use, modify, and distribute this software
- ✅ You **can** use it in personal and commercial projects
- ⚠️ You **must** give visible credit to the original author
- ⚠️ You **must** include the license file in any copies
- ❌ You **cannot** claim this as your own original work

### Required Attribution:
If you use this project, you **must** include the following credit:

> **Built upon [Fake News Detector AI](https://github.com/imkoushal/fake-news-detector-ai) by [Koushal Ray](https://github.com/imkoushal)**

See the full [LICENSE](LICENSE) file for details.

---

<p align="center">
  <strong>Status:</strong> ✅ Production Ready &nbsp;|&nbsp;
  <strong>Version:</strong> 8.0 &nbsp;|&nbsp;
  <strong>Endpoints:</strong> 14 &nbsp;|&nbsp;
  <strong>Rating:</strong> 8.2/10
</p>

<p align="center">
  Made with ❤️ by <a href="https://github.com/imkoushal"><strong>Koushal Ray</strong></a>
</p>
