# 🔍 Fake News Detector AI

A production-ready, multi-layered misinformation detection system combining a high-accuracy Machine Learning ensemble with a **Retrieval-Augmented Generation (RAG)** pipeline for real-time, evidence-based news verification.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [RAG Pipeline](#rag-pipeline)
- [ML Pipeline](#ml-pipeline)
- [Model Performance](#model-performance)
- [Installation](#installation)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Evaluation & Monitoring](#evaluation--monitoring)
- [File Structure](#file-structure)
- [Tech Stack](#tech-stack)

---

## 📖 Overview

The **Fake News Detector AI** is a state-of-the-art misinformation detection system that tackles fake news from two complementary angles:

1. **Linguistic Analysis (ML):** A 5-model Voting Ensemble trained on 100,000+ articles detects the *writing style* of fake news — sensationalism, conspiracy language, clickbait patterns, and structural anomalies.
2. **Factual Verification (RAG):** A Retrieval-Augmented Generation pipeline queries live news via GNews, injects the results into a Groq LLaMA 3 prompt, and cross-references the article's claims against real-time evidence.

This dual approach means the system can catch both *stylistically* fake articles (clickbait, conspiracy blogs) and *factually* fake articles (fabricated events, outdated claims presented as new).

---

## ✨ Key Features

### 🧠 RAG-Powered Real-Time Verification
- Extracts keywords from user input and queries the **GNews API** for live headlines.
- Injects live news context directly into the **Groq LLaMA 3** prompt.
- The AI cross-references article claims against breaking news evidence.
- **Intelligent Fallback:** Automatically switches to standalone style-analysis mode if no live news is found.

### 🌐 Multi-Source Intelligence & Caching (v7.0 Upgrades)
- **Google Fact Check API:** Directly queries Google's ClaimReview database to find if claims have already been verified by trusted orgs (Reuters, AFP, Alt News, etc.).
- **Google Safe Browsing API:** Extracts URLs from article text and scans them for malware, phishing, and social engineering threats.
- **Source Credibility Database:** Built-in domain reputation system covering 80+ Indian and international news sources, graded by credibility tier, category, and bias.
- **Claim Caching Engine:** In-memory TTL cache with normalized hashing that sits in front of external APIs, providing a **160x speedup** on repeated viral claims.

### 🎓 Advanced Features (v8.0 Upgrades)
- **Educator Mode:** Toggle-based step-by-step pipeline transparency showing exactly how each analysis step reached its conclusion — text preprocessing, ML ensemble voting, meta-feature extraction, AI cross-reference, live news retrieval, and fact-check results.
- **Voice Input (Groq Whisper):** Upload WhatsApp voice notes, audio files, or record directly from the browser microphone. Audio is transcribed via Groq Whisper (supports Hindi, English, 50+ languages) and fed into the full analysis pipeline.
- **India Threat Scanner:** 9-category threat detection engine with 150+ India-specific keywords covering UPI/banking fraud, fake government schemes, WhatsApp forward patterns, health misinformation, communal triggers, fake job scams, religious manipulation, India-specific conspiracies, and fake reward/lottery schemes.
- **Community Dashboard:** Live platform-wide stats bar showing total analyses, fake detection rate, average confidence, and today's activity — powered by anonymized aggregated data.

### 🤖 5-Model Voting Ensemble
- **Soft Voting Classifier** combining Logistic Regression, Random Forest, SGD Classifier, LinearSVC (calibrated), and LightGBM.
- Averaged probability outputs with an **F1-optimized decision threshold** (0.552).
- Custom class weights `{FAKE: 1.0, REAL: 1.5}` to minimize false positives on real articles.

### 🧬 Hybrid Feature Engineering
- **TF-IDF Vectorization:** 25,000 n-gram features (unigrams to trigrams) with sublinear TF scaling.
- **20 Custom Meta-Features:** Extracted from raw text before cleaning — captures signals like `all_caps_ratio`, `conspiracy_score`, `sensationalism_score`, `flesch_kincaid_grade`, `clickbait_score`, and `has_attribution`.
- **NUM Token Masking:** Numbers are normalized to `<NUM>` tokens during preprocessing to preserve sentence structure for TF-IDF.

### 🛡️ Out-of-Distribution (OOD) Detection
- Computes TF-IDF centroid distance during inference.
- Flags non-news inputs (recipes, code, poetry) before the model makes a blind guess.
- Dynamic weight shifting reduces ML influence on OOD articles.

### 🏥 Production Monitoring
- SQLite-based prediction tracking (`analysis_history.db`).
- Automated health alerts for drift detection, OOD spikes, and confidence anomalies.
- Comprehensive evaluation reports (JSON/PDF).

### 🎨 Modern Web Frontend
- Responsive dashboard with real-time analysis progress indicators.
- Dynamic "AI + LIVE NEWS" badge when RAG mode activates.
- Adjustable sensitivity slider with live numeric tooltip.
- User authentication and analysis history.

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
  │  ML Pipeline │  │ RAG Pipeline│  │ Model Monitor    │
  │              │  │ (Smart      │  │ (Health Tracking)│
  │ TF-IDF +    │  │  Verify)    │  │                  │
  │ 20 Meta     │  │             │  │ • Drift Detection│
  │ Features    │  │ Step 1:     │  │ • OOD Frequency  │
  │      │      │  │  Keywords   │  │ • Confidence     │
  │      ▼      │  │      │      │  │   Distribution   │
  │ 5-Model     │  │      ▼      │  └──────────────────┘
  │ Voting      │  │ Step 2:     │
  │ Ensemble    │  │  GNews API  │
  │      │      │  │      │      │
  │      ▼      │  │      ▼      │
  │ REAL/FAKE   │  │ Step 3:     │
  │ + Confidence│  │  Inject     │
  └──────────────┘  │  Context   │
                    │      │      │
                    │      ▼      │
                    │ Step 4:     │
                    │  Groq LLaMA │
                    │      │      │
                    │      ▼      │
                    │ VERDICT +   │
                    │ Evidence    │
                    └─────────────┘
```

---

## 🔄 RAG Pipeline

**Retrieval-Augmented Generation** solves the LLM knowledge cutoff problem. Instead of asking the AI to rely on its training data (closed-book), RAG lets it search live news first (open-book).

### How It Works

| Step | Action | Detail |
|------|--------|--------|
| 1 | **Keyword Extraction** | NLP extracts the 3–5 most critical entities from the article |
| 2 | **Live Retrieval** | Keywords are sent to GNews API → returns top headlines + sources |
| 3 | **Prompt Augmentation** | Headlines are injected into the Groq system prompt as factual context |
| 4 | **Fact-Checked Generation** | LLaMA reads the article + live news and outputs a cross-referenced verdict |

### Intelligent Fallback
- If GNews returns **live results** → **RAG mode** (AI + Live News verification)
- If GNews returns **no results** → **Standalone mode** (style-based analysis only)
- The system never breaks — it gracefully degrades to the best available method.

### Example
> **User submits:** *"Apple releases transparent iPhone today"*
>
> **Step 1:** Keywords extracted → `Apple transparent iPhone release`
>
> **Step 2:** GNews returns → *"Apple announces iPhone 16 at September event" (Reuters)*
>
> **Step 3:** Prompt to LLaMA includes the Reuters headline as evidence
>
> **Step 4:** LLaMA verdict → **LIKELY_FALSE** — *"No credible source reports a transparent iPhone. Live news coverage shows Apple released the iPhone 16."*

---

## 🤖 ML Pipeline

### Preprocessing
1. **Number Masking:** `\b\d+\b` → `NUM` (preserves sentence structure)
2. **Text Cleaning:** Lowercasing, URL/HTML removal, special character stripping
3. **Lemmatization:** spaCy `en_core_web_sm` reduces words to base forms
4. **Stopword Removal:** Custom enhanced stopword list

### Feature Extraction (Two-Pronged)
| Branch | Input | Output | Details |
|--------|-------|--------|---------|
| **TF-IDF** | Cleaned text | 25,000 features | 1–3 word n-grams, sublinear TF, max_df=0.85 |
| **Meta-Features** | Raw text | 20 features | Caps ratio, exclamation ratio, conspiracy score, readability, attribution, clickbait score |

Both branches are merged via `scipy.sparse.hstack` into a 25,020-dimensional feature matrix.

### Ensemble Model
| Model | Type | Key Config |
|-------|------|------------|
| Logistic Regression | Linear | RandomizedSearchCV tuned, C=6.80 |
| Random Forest | Tree-based | 100 estimators, max_depth=15 |
| SGD Classifier | Linear | Modified Huber loss |
| LinearSVC | Linear | Calibrated via sigmoid method |
| LightGBM | Gradient Boosted | 200 estimators, 80 leaves |

All models use custom class weights `{0: 1.0, 1: 1.5}` to reduce false positives on real articles. Final prediction uses **Soft Voting** (averaged probabilities) with an **F1-optimized threshold of 0.552**.

---

## 📈 Model Performance

### ML Ensemble (v6.0 — Latest)

| Metric | Score |
|--------|-------|
| **Accuracy** | **94.77%** |
| Precision | 95.81% |
| Recall | 93.66% |
| F1-Score | 94.72% |
| ROC-AUC | 99.09% |

### Per-Class Breakdown

| Class | Precision | Recall | F1 |
|-------|-----------|--------|-----|
| FAKE | 94% | 96% | 95% |
| REAL | 96% | 94% | 95% |

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
```

---

## 💻 Usage

### Web Dashboard (Frontend)
```bash
# Start the FastAPI backend
uvicorn api:app --port 8000

# Open frontend/index.html in your browser
```

### Streamlit Dashboard
```bash
streamlit run app.py
```
Access at **http://localhost:8501**

### REST API
```bash
uvicorn api:app --port 8000
```
Access API docs at **http://localhost:8000/docs**

### Retrain the Model
```bash
python train.py
```

---

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/analyze` | POST | ML-only prediction (fast, no API calls) |
| `/api/v1/smart-verify` | POST | **RAG pipeline** — GNews search → Groq LLaMA verification |
| `/api/v1/fact-check` | POST | Google Fact Check API integration |
| `/api/v1/safe-browsing` | POST | URL threat detection via Google Safe Browsing |
| `/api/v1/source-credibility` | POST | Domain reputation scoring (80+ sources) |
| `/api/v1/india-threat-scan` | POST | India-specific scam/misinfo pattern detection |
| `/api/v1/transcribe` | POST | Audio transcription via Groq Whisper |
| `/api/v1/community-stats` | GET | Platform-wide anonymized analysis stats |
| `/api/v1/cache-stats` | GET | Monitor hit/miss rates of the Claim Cache |
| `/api/v1/gemini-verify` | POST | Standalone AI style analysis (legacy) |
| `/api/v1/gnews-search` | POST | Manual web search (legacy) |
| `/api/v1/health` | GET | Server health check |
| `/api/v1/model-info` | GET | Current model version and metadata |

### Smart Verify Request
```json
{
  "text": "Your news article text here..."
}
```

### Smart Verify Response
```json
{
  "verdict": "LIKELY_TRUE",
  "credibility_score": 85,
  "analysis": "The article's claims are supported by live news...",
  "mode": "rag",
  "web": {
    "total_articles": 5,
    "trusted_count": 3,
    "articles": [...]
  }
}
```

---

## 📊 Evaluation & Monitoring

### Generate Evaluation Report
```bash
python eval_report.py
python eval_report.py --json
python eval_report.py --save  # Saves to logs/eval_report.json
```

### WelFake Cross-Domain Evaluation
```bash
python eval_welfake.py
```

### Monitor Tests
```bash
pytest tests/test_monitoring.py -v
```

---

## 📁 File Structure

```
fake-news-detector-ai/
├── api.py                      # FastAPI backend (ML + RAG + Auth)
├── app.py                      # Streamlit web dashboard
├── train.py                    # ML training pipeline (5-model ensemble)
├── utils.py                    # NLP text cleaning & preprocessing
├── meta_features.py            # 20 custom linguistic feature extractors
├── ood_detector.py             # Out-of-Distribution scoring & weighting
├── model_monitor.py            # SQLite production health tracking
├── eval_report.py              # Performance report generator
├── eval_welfake.py             # WelFake cross-domain evaluation
├── cross_domain_eval.py        # Cross-dataset validation matrix
├── database.py                 # User auth & analysis history DB
├── enhanced_features.py        # Extended feature generation
│
├── frontend/                   # Modern web UI
│   ├── index.html              # Dashboard HTML
│   ├── app.js                  # Frontend logic (Smart Verify integration)
│   └── styles.css              # UI styling
│
├── models/                     # Trained model artifacts
│   ├── model.joblib            # Voting ensemble
│   ├── tfidf.joblib            # TF-IDF vectorizer
│   ├── scaler.joblib           # Meta-feature scaler
│   ├── ood_centroid.npy        # OOD detection centroid
│   └── config.json             # Model metadata & threshold
│
├── data_new/                   # Training datasets
│   ├── True.csv                # Real news articles
│   ├── Fake.csv                # Fake news articles
│   ├── WELFake_Dataset.csv     # WELFake benchmark
│   └── liar/                   # LIAR fact-check dataset
│
├── tests/                      # Test suite
│   ├── test_model_quality.py   # Prediction assertions
│   └── test_monitoring.py      # Health monitor unit tests
│
├── logs/                       # Experiment logs & eval reports
├── portfolio/                  # Project portfolio page
├── .env.example                # Environment variable template
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container deployment
└── docker-compose.yml          # Multi-service orchestration
```

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Backend** | FastAPI (Python) | REST API, async request handling |
| **ML Framework** | Scikit-Learn, LightGBM | Ensemble training & inference |
| **NLP** | spaCy, NLTK, TF-IDF | Text processing & feature extraction |
| **LLM** | Groq API (LLaMA 3) | RAG-powered fact-checking |
| **External APIs** | GNews, Google Fact Check, Safe Browsing | Live verification & threat detection |
| **Frontend** | HTML, CSS, JavaScript | Modern responsive dashboard |
| **Database** | SQLite, In-Memory LRU Cache | User auth, history, fast claim caching |
| **Deployment** | Docker, Render | Containerized cloud deployment |

---

**Status:** ✅ Production Ready
**Model Version:** 8.0 (ML + RAG + Multi-Source Intelligence + India Threat Scanner)
**Total API Endpoints:** 14
**Author:** [Koushal](https://github.com/imkoushal)
