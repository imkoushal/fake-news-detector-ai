# 🔍 Hybrid Fake News Detector

A state-of-the-art machine learning system for detecting misinformation in news articles, powered by an ensemble model trained on 157,000+ articles from multiple datasets.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Status](#project-status)
- [Architecture](#architecture)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Model Performance](#model-performance)
- [Usage](#usage)
- [Important Usage Notes](#important-usage-notes)
- [API Integration](#api-integration)
- [File Structure](#file-structure)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

---

## 📖 Overview

The **Hybrid Fake News Detector** is a production-ready machine learning application that identifies misinformation in news articles using a sophisticated ensemble approach combined with AI analysis and web verification.

### System Layers

1. **ML Model Layer** - 5-model ensemble with advanced TF-IDF vectorization
2. **AI Analysis Layer** - Google Gemini AI for credibility assessment  
3. **Web Verification Layer** - Real-time GNews API integration for source corroboration

### Key Achievements

✅ **96.46% Accuracy** on test set with 59,220 balanced training samples
✅ **95.84% Precision** - Reliable fake news detection
✅ **97.14% Recall** - Catches vast majority of fake news
✅ **97.10% Validation** - Verified on 1,000 independent samples
✅ **Production Ready** - Fully operational deployment with Streamlit interface

---

## ✨ Features

### 🤖 Machine Learning Engine
- **Advanced Ensemble Classifier** combining 5 algorithms:
  - Logistic Regression (optimized)
  - SGD Classifier (stochastic gradient descent)
  - Calibrated LinearSVC (wrapped for probability support)
  - Random Forest (200 estimators)
  - Gradient Boosting (100 estimators)
- **Soft Voting** for weighted probability combination
- **8,000 TF-IDF Features** with trigrams (1-3)
- **Enhanced Text Processing**:
  - Removes words shorter than 3 characters
  - Filters noise and common words
  - min_df=3, max_df=0.8 for optimal feature selection
- **Multiple Dataset Training**:
  - ISOT Dataset: 44,898 articles
  - WELFake Dataset: 72,134 articles
  - Kaggle Fake-Real: 34,416 articles
  - fake_or_real_news: 6,335 articles
  - **Total: 157,783 articles** (59,220 balanced for training)

### 🎯 NEW: Explainable AI
- **Individual Model Predictions** - See how each of the 5 ensemble models voted
- **Suspicious Phrase Detection** - Highlights clickbait, conspiracy theories, medical misinformation
- **Word Importance Analysis** - TF-IDF feature visualization showing influential words
- **Severity Indicators** - Color-coded flags (🔴 High, 🟡 Medium, 🟢 Low)

### 📊 NEW: Historical Tracking Dashboard
- **SQLite Database** - Stores all analysis history in `analysis_history.db`
- **Statistics Visualization** - Total analyses, Real vs Fake distribution (pie chart)
- **Topic Categorization** - Bar charts showing article categories
- **History Table** - Last 50 analyses with timestamps
- **CSV Export** - Download complete history for external analysis
- **Top Red Flags** - Shows articles with highest suspicious scores

### 🔍 NEW: Advanced Source Analysis
- **Domain Extraction** - Automatically detects URLs in text
- **Trusted Source Database** - Pre-loaded with 19 major news outlets (Reuters, BBC, AP, NYTimes, etc.)
- **Reputation Scoring** - 0-100 score based on historical performance
- **Source Categories** - Trusted, Unreliable, or Unknown classification

### 📝 NEW: User Feedback System
- **5-Star Rating** - Users rate prediction accuracy
- **Feedback Storage** - All ratings saved to database for model improvement
- **Correct Label Collection** - Users can provide actual classification
- **Future Training Data** - Feedback can be used to retrain model

### 📂 NEW: Advanced Categorization
- **Topic Classification** - Automatically categorizes into 6 topics:
  - Politics, Health, Technology, Science, Business, Entertainment
- **Confidence Scores** - Shows how confident the categorization is
- **Keyword Matching** - Uses topic-specific keyword dictionaries
- **Readability Analysis** - Flesch-Kincaid reading level, difficulty rating, sentence/word stats

### 🌐 NEW: REST API
- **FastAPI Framework** - High-performance async API
- **Endpoints:**
  - `GET /health` - Health check
  - `POST /api/v1/analyze` - Single article analysis
  - `POST /api/v1/batch` - Batch processing (up to 50 articles)
  - `GET /api/v1/stats` - Usage statistics
- **API Key Authentication** - Secure endpoint access
- **Rate Limiting** - 30/min for single, 10/min for batch
- **CORS Enabled** - Cross-origin requests supported
- **OpenAPI Docs** - Auto-generated at `/docs`

### 🌙 NEW: Dark Mode & UI Enhancements
- **Dark Mode Toggle** - Enable/disable dark theme in sidebar
- **Custom CSS** - Dark background and text colors
- **Text Area Styling** - Themed input boxes
- **4-Tab Interface** - Analysis, Batch Processing, Settings, Dashboard
- **Mobile-Responsive** - Optimized for all screen sizes

### 🧠 AI-Powered Analysis
- **Google Gemini 2.5 Flash** integration
- **API Reference:** [Google AI for Developers - Gemini API](https://ai.google.dev/gemini-api/docs)
- **Model Used:** gemini-2.0-flash-exp
- **7-Factor Analysis**:
  1. Source credibility assessment
  2. Evidence quality evaluation
  3. Emotional manipulation detection
  4. Logical fallacy identification
  5. Red flag analysis
  6. Conspiracy indicator scoring
  7. Sensationalism detection

### 🌐 Web Verification
- **GNews API Integration** for real-time source verification
- **API Reference:** [GNews API Documentation](https://gnews.io/docs/v4)
- **Endpoint:** https://gnews.io/api/v4/search
- **Trusted Source Detection** (Reuters, BBC, AP, etc.)
- **Article Cross-Reference** with credible publications
- **Confidence Boosting** through multiple independent sources

### 🚩 Red Flag Detection System
Sophisticated pattern matching for:
- Medical misinformation ("doctors don't want you to know")
- Clickbait detection ("this one weird trick")
- Conspiracy theories ("big pharma", "deep state")
- Censorship claims ("share before deleted")
- Unsubstantiated medical fraud patterns
- Excessive sensational punctuation

---

## ✅ Project Status: FULLY OPERATIONAL

| Component | Status | Details |
|-----------|--------|---------|
| ML Model | ✅ Trained | 96.46% accuracy, 5-algorithm ensemble |
| Training Data | ✅ Complete | 59,220 balanced articles from 4 datasets |
| Gemini AI | ✅ Integrated | 7-factor credibility analysis |
| GNews API | ✅ Active | Real-time source verification |
| Web Interface | ✅ Live | Streamlit dashboard at localhost:8501 |
| Text Processing | ✅ Enhanced | Removes short words, advanced cleaning |
| Red Flag Detection | ✅ Active | Pattern-based fake news indicators |

---

## 🏗️ Architecture

Multi-layer verification system with weighted decision making:

```
Article Input → ML Model (50%) + Gemini AI (30%) + GNews (20%)
                        ↓
                  FINAL VERDICT
                  + Confidence Score
                  + Red Flag Analysis
```

---

## 🚀 Installation

### Prerequisites
- Python 3.10+
- 500MB disk space

### Quick Setup
```bash
cd "c:\Users\lenovo\Desktop\fake news dector"
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### Configure APIs
Edit `app.py` with your API keys:
```python
GEMINI_API_KEY = "your_key"  # Get from: https://ai.google.dev/
GNEWS_API_KEY = "your_key"   # Get from: https://gnews.io/
```

**API Key Sources:**
- **Gemini API:** https://ai.google.dev/ (Free tier: 15 requests/minute, 1,500 requests/day)
- **GNews API:** https://gnews.io/dashboard (Free tier: 100 requests/day)

---

## ⚡ Quick Start

```bash
# Activate virtual environment
cd "c:\Users\lenovo\Desktop\fake news dector"
.venv\Scripts\Activate.ps1

# Run web application
.venv\Scripts\python.exe -m streamlit run app.py

# Run REST API (optional - in separate terminal)
python api.py

# Retrain model (if needed)
python train_advanced.py
```

Access web app at: **http://localhost:8501**  
Access API docs at: **http://localhost:8000/docs**

### First-Time Setup
```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run app
.venv\Scripts\python.exe -m streamlit run app.py
```

---

## 📊 Model Performance

### Test Results (Advanced Ensemble Model v2.0)

| Metric | Score |
|--------|-------|
| **Accuracy** | **96.46%** |
| Precision | 95.84% |
| Recall | 97.14% |
| F1-Score | 96.48% |
| REAL Accuracy | 95.79% |
| FAKE Accuracy | 97.14% |

### Validation Results
- **Quick Test:** 97.10% on 1,000 WELFake samples
- **Final Validation:** 100% on 50 balanced samples
- **Training Data Test:** 100% on random ISOT samples

### Training Data
- **Total Available:** 157,783 articles from 4 datasets
- **Training Set:** 59,220 balanced articles (29,610 real, 29,610 fake)
- **Test Accuracy:** 96.46% on unseen data
- **Model Version:** 2.0_advanced
- **Training Date:** November 2025

### Datasets Used
1. **ISOT Dataset** - 44,898 articles (Reuters, political news)
2. **WELFake Dataset** - 72,134 articles (diverse sources)
3. **Kaggle Fake-Real** - 34,416 articles (balanced dataset)
4. **fake_or_real_news** - 6,335 articles (supplementary data)

---

## 💻 Usage

### Web Application (Streamlit)

#### Tab 1: Single Article Analysis
1. **Paste full-length article text** (minimum 500-1000 characters recommended)
2. Click "🔍 Analyze"
3. View prediction (REAL/FAKE)
4. Check confidence score & red flags
5. Read Gemini AI analysis & web sources
6. **NEW:** See individual model predictions in "Why This Prediction?" section
7. **NEW:** View suspicious phrases with severity levels
8. **NEW:** Check topic classification and readability scores
9. **NEW:** Rate prediction accuracy (1-5 stars)

#### Tab 2: Bulk Processing
1. Upload CSV with articles
2. Model analyzes all rows
3. **NEW:** View progress bar during processing
4. Download results with detailed analysis

#### Tab 3: Settings
- Adjust sensitivity slider: 0.0 (strict) → 1.0 (lenient)
- **NEW:** Toggle dark mode
- Configure analysis options

#### Tab 4: Dashboard (NEW)
- **Overall Statistics** - Total analyses, Real/Fake distribution
- **Pie Chart** - Visual breakdown of predictions
- **Bar Chart** - Topic distribution across analyzed articles
- **Recent History** - Table of last 50 analyses with timestamps
- **CSV Download** - Export complete analysis history
- **Top Red Flags** - Articles with highest suspicious scores

### REST API

#### Start API Server
```bash
python api.py
# Server runs on http://localhost:8000
# API docs at http://localhost:8000/docs
```

#### Example API Calls
```bash
# Health check
curl http://localhost:8000/health

# Analyze single article
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "X-API-Key: demo_key_123" \
  -H "Content-Type: application/json" \
  -d '{"text":"Your article text here..."}'

# Batch analysis
curl -X POST http://localhost:8000/api/v1/batch \
  -H "X-API-Key: demo_key_123" \
  -H "Content-Type: application/json" \
  -d '{"articles":[{"text":"Article 1"},{"text":"Article 2"}]}'

# Get statistics
curl http://localhost:8000/api/v1/stats \
  -H "X-API-Key: demo_key_123"
```

See **API_GUIDE.md** for complete API documentation and browser extension setup.

### Database Queries

```python
from database import AnalysisDatabase

db = AnalysisDatabase()

# Get all history
history = db.get_history(limit=100)

# Get statistics
stats = db.get_statistics()
print(f"Total analyses: {stats['total_analyses']}")
print(f"Fake percentage: {stats['fake_percentage']:.1f}%")

# Add feedback
db.add_feedback(
    article_hash="abc123",
    rating=5,
    correct_label="FAKE",
    feedback_text="Prediction was accurate"
)
```

---

## ⚠️ Important Usage Notes

### Article Length Requirements
The model was trained on **full-length news articles** averaging 2,400 characters (~400-500 words). For accurate predictions:

✅ **Recommended:** 500+ characters (full article text)
❌ **Not Recommended:** Short snippets, headlines only, brief summaries

**Why?** The model analyzes linguistic patterns, writing style, and contextual indicators that only appear in complete articles. Short text lacks sufficient features for reliable classification.

### Best Practices
- **Use complete articles** - Include full body text, not just headlines
- **Paste from original source** - Avoid edited or truncated versions
- **Check character count** - App shows real-time feedback
- **Expect warnings** - App alerts when text is too short (<500 chars)

### Testing Examples
The file `test_full_articles.txt` contains properly formatted examples:
- **Real News:** Federal Reserve article (1,867 chars) → 82% REAL confidence ✓
- **Fake News:** Diabetes cure scam (2,028 chars) → 95% FAKE confidence ✓

---

## 🔌 API Features

### Gemini AI Analysis
- Source credibility assessment
- Evidence quality evaluation
- Emotional manipulation detection
- Logical fallacy identification
- Red flag analysis
- Conspiracy indicators
- Sensationalism scoring

### GNews Verification
- Real-time article search
- Trusted source detection
- Publication pattern analysis
- Cross-reference checking

---

## 🧠 Advanced Model Details

### Ensemble Architecture
```
Input Text → Text Cleaning → TF-IDF (8000 features) → 5 Models
                                                          ↓
                                                    Soft Voting
                                                          ↓
                                                  Final Prediction
```

### Text Preprocessing Pipeline
1. Convert to lowercase
2. Remove URLs and email addresses
3. Remove special characters (keep alphanumeric + spaces)
4. Remove extra whitespace
5. **Remove words shorter than 3 characters** (critical for accuracy)
6. Strip leading/trailing spaces

### TF-IDF Configuration
- **max_features:** 8000
- **ngram_range:** (1, 3) - unigrams, bigrams, trigrams
- **min_df:** 3 - word must appear in at least 3 documents
- **max_df:** 0.8 - ignore words in >80% of documents
- **stop_words:** 'english'

### Model Components
1. **LogisticRegression** - Linear classification baseline
2. **SGDClassifier** - Stochastic gradient descent
3. **CalibratedClassifierCV(LinearSVC)** - SVM with probability calibration
4. **RandomForestClassifier** - 200 trees ensemble
5. **GradientBoostingClassifier** - 100 boosting iterations

### Voting Strategy
- **Soft voting** - Averages probability predictions from all models
- **Threshold:** 0.5 (balanced classification)
- **Output:** probability[0]=REAL, probability[1]=FAKE

---

## 📁 File Structure

```
fake news detector/
├── app.py                      # Main Streamlit web application (4 tabs + dashboard)
├── api.py                      # NEW: FastAPI REST API server
├── database.py                 # NEW: SQLite database integration
├── enhanced_features.py        # NEW: Source analysis, topic classification, readability
├── train_advanced.py           # Advanced ensemble training script
├── requirements.txt            # Python dependencies (includes fastapi, plotly, etc.)
├── README.md                   # This documentation
├── API_GUIDE.md                # NEW: API and browser extension documentation
├── FEATURES.md                 # NEW: Complete feature documentation
├── test_full_articles.txt      # Full-length test examples
├── test_new_features.py        # NEW: Feature testing script
├── analysis_history.db         # NEW: SQLite database (created on first use)
├── data_new/                   # Training datasets
│   ├── Fake.csv               # ISOT fake news (23,481)
│   ├── True.csv               # ISOT real news (21,417)
│   ├── WELFake_Dataset.csv    # WELFake dataset (72,134)
│   └── liar/                  # LIAR dataset
│       ├── train.tsv
│       ├── test.tsv
│       └── valid.tsv
├── models/                     # Trained model files
│   ├── model.joblib           # Ensemble classifier
│   ├── tfidf.joblib           # TF-IDF vectorizer
│   └── config.json            # Model configuration
└── .venv/                      # Python virtual environment
```

### Key Files
- **app.py** (1100+ lines) - Production Streamlit interface with dashboard, explainable AI
- **api.py** (255 lines) - FastAPI server with authentication, rate limiting
- **database.py** (267 lines) - SQLite integration with 3 tables
- **enhanced_features.py** (185 lines) - 8 analysis functions for advanced features
- **train_advanced.py** (361 lines) - Training script achieving 96.46% accuracy
- **models/model.joblib** - 5-model ensemble classifier (VotingClassifier)
- **models/tfidf.joblib** - Trained TF-IDF vectorizer with 8000 features
- **models/config.json** - Performance metrics and model metadata

---

## ⚙️ Configuration

### Model Config (models/config.json)
```json
{
  "accuracy": 0.9646,
  "precision": 0.9584,
  "recall": 0.9714,
  "f1_score": 0.9648,
  "real_accuracy": 0.9579,
  "fake_accuracy": 0.9714,
  "threshold": 0.5,
  "model_version": "2.0_advanced",
  "training_samples": 59220,
  "training_date": "2025-11-29",
  "max_features": 8000,
  "ngram_range": [1, 3],
  "ensemble_models": 5
}
```

### API Configuration
Edit `app.py` to configure:
```python
GEMINI_API_KEY = "your_gemini_api_key"
GNEWS_API_KEY = "your_gnews_api_key"
```

---

## 🔧 Troubleshooting

| Issue | Solution |
|-------|----------|
| Model not loading | Model files exist: `models/model.joblib` & `models/tfidf.joblib` |
| Short articles classified wrong | Use full-length articles (500+ chars), not headlines |
| Streamlit won't start | Use: `.venv\Scripts\python.exe -m streamlit run app.py` |
| Gemini API errors | Check API key validity at https://ai.google.dev/ |
| GNews 401 error | Regenerate key at https://gnews.io/dashboard |
| "FAKE" for real news | Article too short - model needs 500+ characters |
| Low confidence scores | Provide more context, complete sentences |
| Import errors | Ensure virtual environment activated |

### Common Fixes
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Retrain model
python train_advanced.py

# Check model files exist
ls models/

# Test preprocessing
python -c "from app import clean_text; print(clean_text('test article text'))"
```

---

## 📈 Performance Tips

### Optimal Accuracy
- **Use full articles** (500+ characters minimum)
- Enable all 3 verification layers (ML + AI + Web)
- Lower sensitivity slider for stricter detection
- Provide complete context and full sentences

### Faster Predictions
- Disable Gemini AI analysis (ML model only)
- Skip web verification for offline use
- Process articles in batches

### Production Deployment
- Use model files: `model.joblib` + `tfidf.joblib`
- Implement caching for repeated queries
- Monitor API quotas (Gemini, GNews)
- Log predictions for analysis

### Retraining the Model
```bash
# Run training script (takes ~5-10 minutes)
python train_advanced.py

# Outputs:
# - models/model.joblib (ensemble classifier)
# - models/tfidf.joblib (vectorizer)
# - models/config.json (metrics)
```

Training uses:
- 59,220 balanced samples
- 5-model ensemble
- 8,000 TF-IDF features
- Achieves 96.46% accuracy

---

## 🎯 Use Cases

- **Newsrooms:** Pre-publication verification of sources
- **Social Media:** Content moderation and fact-checking
- **Research:** Academic studies on misinformation patterns
- **Education:** Teaching news literacy and critical thinking
- **Fact-checking Organizations:** Automated initial screening
- **Browser Extensions:** Real-time article verification
- **Content Platforms:** Automated flagging systems

---

## 📝 Technical Details

### Why 96.46% vs Higher Claims?
This model prioritizes **real-world generalization** over overfitting:
- Trained on diverse datasets (ISOT, WELFake, Kaggle, etc.)
- Tested on completely unseen data
- No data leakage or test set contamination
- Realistic performance expectations

### Model Limitations
- **Requires full articles** - Cannot reliably classify headlines or short snippets
- **English only** - Trained exclusively on English news
- **News domain** - Optimized for news articles, not social media posts
- **Context dependent** - Needs complete sentences and proper structure
- **No real-time learning** - Requires retraining for new patterns

### Future Improvements
- [ ] Multi-language support
- [ ] Real-time model updates
- [ ] Social media post optimization
- [ ] Short-text classification mode
- [ ] Explanation generation for predictions

---

**Status:** ✅ Production Ready  
**Accuracy:** 96.46% (Test) | 97.10% (Validation)  
**Last Updated:** November 29, 2025  
**Model Version:** 2.0_advanced
