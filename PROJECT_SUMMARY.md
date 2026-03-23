# Fake News Detector - Complete Project Summary

## 📋 Project Overview

**Hybrid Fake News Detector** is a production-ready machine learning application designed to identify misinformation in news articles using a sophisticated ensemble approach. It combines:
- ML Model (50% weight): 5-algorithm ensemble with 96.46% accuracy
- AI Analysis (30% weight): Google Gemini 2.5 Flash for credibility assessment
- Web Verification (20% weight): GNews API for real-time source corroboration

**Current Status**: ✅ FULLY OPERATIONAL
- 96.46% Accuracy on 59,220 balanced training samples
- 95.84% Precision | 97.14% Recall
- 97.10% Validation on independent samples

---

## 🏗️ Project Architecture

### Multi-Layer Verification System
```
Article Input → ML Model (50%) + Gemini AI (30%) + GNews (20%)
                        ↓
                  FINAL VERDICT
                  + Confidence Score
                  + Red Flag Analysis
```

### Training Data (157,783 articles from 4 datasets)
1. **ISOT Dataset**: 44,898 articles (Reuters, political news)
2. **WELFake Dataset**: 72,134 articles (diverse sources)
3. **Kaggle Fake-Real**: 34,416 articles (balanced dataset)
4. **fake_or_real_news**: 6,335 articles (supplementary data)
- **Final Training Set**: 59,220 balanced articles (29,610 real, 29,610 fake)

---

## 📁 Complete File Structure & Details

### Root Level Python Files

#### **app.py** (Main Streamlit Application - 1100+ lines)
- **Purpose**: Production Streamlit interface with 4-tab layout
- **Key Features**:
  - `load_model()`: Loads 5-model ensemble (pipeline.joblib or model.joblib + tfidf.joblib)
  - Dark mode toggle with custom CSS styling
  - Session state management
  - Renders all 4 pages via imported page modules
- **Configuration**:
  - GNEWS_API_KEY: "84750e988d2d3e69c1c5e94293393433"
  - GEMINI_API_KEY: "AIzaSyBa8Txd9gDph1tMP4h7A8iNkWiNN5UrQ3Q"
- **Model Loading Priority**:
  1. models/model.joblib + models/tfidf.joblib (preferred)
  2. models/pipeline_optimized.joblib (fallback)
  3. models/pipeline.joblib (final fallback)

#### **api.py** (FastAPI REST Server - 255 lines)
- **Purpose**: High-performance async REST API with rate limiting
- **Features**:
  - CORS middleware for cross-origin requests
  - Rate limiting: 30/min for single, 10/min for batch
  - API Key authentication (demo_key_123, prod_key_456)
  - Soft voting probability predictions
- **Endpoints**:
  - `GET /` - API root
  - `GET /health` - Health check
  - `POST /api/v1/analyze` - Single article analysis
  - `POST /api/v1/batch` - Batch processing (max 50 articles)
  - `GET /api/v1/stats` - Usage statistics
- **Dependencies**: FastAPI, Uvicorn, SlowAPI, Pydantic
- **Auto-generated docs**: http://localhost:8000/docs

#### **api_client.py** (API Client Module - 70 lines)
- **Purpose**: Client functions for external API integration
- **Key Functions**:
  - `get_gemini_client()`: Initialize Gemini API client
  - `gemini_verify_claim()`: AI-powered credibility assessment
  - `search_news_gnews()`: Search GNews for related articles
  - `check_gnews_api()`: Verify GNews connection status
  - `translate_text()`: Translate text using Gemini API
- **Handles**:
  - API connection errors gracefully
  - Quality filtering for GNews results
  - Timeouts and retry logic

#### **database.py** (SQLite Integration - 267 lines)
- **Purpose**: Persistent storage for analysis history and user feedback
- **Tables**:
  1. `analysis_history`: Stores article analyses (MD5 hash unique)
  2. `user_feedback`: User ratings and corrections
  3. `source_reputation`: Domain credibility tracking
- **Key Methods**:
  - `add_analysis()`: Store analysis results
  - `add_feedback()`: Record user ratings
  - `get_history()`: Retrieve recent analyses
  - `get_statistics()`: Calculate dashboard metrics
  - `update_source_reputation()`: Track domain reliability
- **Database Path**: analysis_history.db (created on first use)

#### **utils.py** (Text Processing Utilities - 200+ lines)
- **Purpose**: Advanced unified text cleaning pipeline
- **Key Functions**:
  - `clean_text()`: Advanced text preprocessing
    - Lowercase conversion
    - URL/email removal
    - HTML tag removal
    - Special character filtering
    - Lemmatization via spaCy (if available)
    - Stopword removal
    - Minimum 3-character word filtering
  - `extract_features()`: Linguistic feature extraction
    - Sentence count, avg length
    - Question/exclamation counts
    - All-caps word analysis
  - `get_conspiracy_indicators()`: Count conspiracy language patterns
  - `get_sensationalism_score()`: Measure sensational language
  - `extract_keywords()`: Extract important keywords for search
- **Uses**: spaCy for advanced NLP (en_core_web_sm)

#### **enhanced_features.py** (Advanced Analysis Module - 185 lines)
- **Purpose**: Explainable AI and advanced classification features
- **Key Functions**:
  - `extract_domain()`: Extract URL/domain from text
  - `analyze_source()`: Evaluate source credibility (trusted/unreliable/unknown)
  - `classify_topic()`: Categorize article into 6 topics:
    - Politics, Health, Technology, Science, Business, Entertainment
  - `get_word_importance()`: TF-IDF feature importance visualization
  - `get_model_predictions()`: Individual ensemble model predictions
  - `highlight_suspicious_phrases()`: Identify red flag patterns
  - `calculate_readability_score()`: Flesch-Kincaid analysis
  - `extract_time_references()`: Detect date/time mentions
  - `detect_fake_news_red_flags()`: Identify obvious misinformation
- **Known Sources**:
  - Trusted: Reuters, BBC, AP, NYTimes, Guardian, Bloomberg, etc. (19 sources)
  - Unreliable: InfoWars, NaturalNews, BeforeItsNews, etc.

#### **train.py** (Model Training Script - 416 lines)
- **Purpose**: Training pipeline for 5-model ensemble
- **Pipeline Steps**:
  1. Load datasets from data/ directory
  2. Combine and clean using utils.clean_text()
  3. Balance dataset (equal real/fake samples)
  4. Split: Train (72%), Val (10%), Test (15%)
  5. TF-IDF Vectorization (8000 features, trigrams)
  6. Train 5 classifiers with GridSearchCV
  7. Create VotingClassifier with soft voting
  8. Calibrate predictions
  9. Evaluate on test set
  10. Log experiments to logs/experiments.csv
- **TF-IDF Configuration**:
  - max_features: 8000
  - ngram_range: (1, 3)
  - min_df: 2, max_df: 0.90
  - sublinear_tf: True
- **Models**:
  1. LogisticRegression (optimized via GridSearch)
  2. SGDClassifier (Stochastic Gradient Descent)
  3. CalibratedClassifierCV(LinearSVC)
  4. RandomForestClassifier (200 trees)
  5. GradientBoostingClassifier (100 iterations)
- **Output Models**:
  - models/model.joblib: Final ensemble
  - models/tfidf.joblib: Vectorizer
  - models/config.json: Performance metrics

#### **state_management.py** (Session State Helper - 30 lines)
- **Purpose**: Streamlit session state initialization
- **Functions**:
  - `init_session_state()`: Initialize global state variables
  - `get_state()`: Retrieve session value
  - `set_state()`: Store session value
- **Managed States**:
  - show_history: Display history modal
  - analysis_results: Store current analysis

#### **ultra_detector.py** (Standalone Detector - 300+ lines)
- **Purpose**: Simplified detection without Streamlit dependency
- **Class**: `UltraDetector`
- **Key Methods**:
  - `predict_ml()`: ML model prediction only
  - `analyze_linguistic()`: Pattern-based analysis
  - `analyze_complete()`: Multi-layer analysis
  - `generate_explanation()`: Human-readable results
  - `get_detailed_report()`: Comprehensive analysis report
- **Use Case**: Standalone script or library integration

#### **ui_components.py** (UI Helper Module - 50 lines)
- **Purpose**: Reusable Streamlit UI components
- **Functions**:
  - `render_header()`: Main app title and metrics
  - `render_sidebar_metrics()`: Model performance display
  - `render_api_status()`: API connectivity indicators
- **Displays**:
  - Accuracy, Precision, Recall, F1-Score
  - False Positive/Negative Rates
  - Training date and sample count

#### **verify_abbreviations.py** (Document Utility - 30 lines)
- **Purpose**: Extract abbreviations from DOCX file
- **Function**: Read Major_Project_Report_New_Complete.docx
- **Output**: Print formatted abbreviations table

---

### App Pages (app_pages/ directory)

#### **app_pages/analyze_page.py** (Single Article Analysis - 405 lines)
- **Purpose**: Main analysis tab with comprehensive output
- **Features**:
  - Text input with character count warning
  - Real-time translation option (Gemini API)
  - ML prediction with confidence score
  - Red flag detection
  - Linguistic feature analysis
  - **Explainable AI**:
    - Individual model predictions (5-model breakdown)
    - Suspicious phrase highlighting with severity levels
    - Topic classification
    - Readability analysis (Flesch-Kincaid)
    - Source credibility analysis
  - **Multi-layer Verification**:
    - Gemini AI 7-factor credibility assessment
    - GNews web search for corroborating articles
    - Related news source table
  - **Final Verdict**:
    - Weighted combination: ML (50%) + Gemini (30%) + Web (20%)
    - Red flag penalty adjustment
    - Confidence calculation with breakdown
    - Recommendation: REAL/FAKE/UNCERTAIN
  - Database storage with user feedback rating system

#### **app_pages/batch_page.py** (Bulk Analysis - 85 lines)
- **Purpose**: CSV file batch processing tab
- **Features**:
  - CSV upload with auto-detection of text column
  - Progress bar during processing
  - Results table with predictions and probabilities
  - CSV download of results
  - Database storage of batch results
- **Supported Columns**: 'text', 'content', 'article', 'body'

#### **app_pages/dashboard_page.py** (Analytics Dashboard - 100 lines)
- **Purpose**: Statistics and history visualization
- **Features**:
  - Top metrics: Total analyzed, Avg confidence, Fake % detected
  - Real vs Fake distribution pie chart
  - Topic distribution bar chart
  - Daily activity trend line chart
  - Recent analyses table (last 50)
  - Top suspicious articles list (red flag >0.5)
  - Full history CSV download

---

### Assets (assets/ directory)

#### **assets/generate_logo.py** (Visual Asset Generator - 200+ lines)
- **Purpose**: Generate professional UI assets
- **Functions**:
  - `create_logo()`: Professional circular logo with purple gradient
  - `create_favicon()`: Browser favicon (64x64 ICO)
  - `create_banner()`: Header banner for README
  - `create_badge()`: Performance badges
- **Output**: assets/logo.png, assets/favicon.ico, etc.

#### **assets/assets/** (Generated Assets Folder)
- Logo, favicon, and badge images (created by generate_logo.py)

---

### Configuration & Data

#### **requirements.txt** (Dependencies - 50+ packages)
**ML/Data Processing**:
- numpy>=2.0.0, pandas==2.3.1
- scikit-learn==1.7.1, joblib==1.5.1
- xgboost==2.0.3, lightgbm==4.6.0

**NLP**:
- spacy>=3.8.0, textblob==0.17.1, vaderSentiment==3.3.2

**Web Framework**:
- streamlit==1.48.1, fastapi==0.115.0, uvicorn==0.32.1

**APIs**:
- google-generativeai==0.8.3, requests==2.32.5
- groq==0.4.2, python-dotenv==1.0.0

**Visualization**:
- plotly==5.24.1, matplotlib==3.10.5
- pillow==11.3.0 (for logo generation)

**Security/Performance**:
- slowapi==0.1.9, pydantic==2.10.3

#### **models/** (Trained Models)
- `model.joblib`: 5-model ensemble classifier
- `tfidf.joblib`: Fitted TF-IDF vectorizer (8000 features)
- `config.json`: Model metadata and performance metrics
- `pipeline.joblib`, `pipeline_optimized.joblib`: Alternative model formats
- `pipeline_svm.joblib`: SVM model variant
- `config_optimized.json`: Optimized configuration

#### **data/** (Original Datasets)
- True.csv: Real news from ISOT
- Fake.csv: Fake news from ISOT

#### **data_new/** (Extended Datasets)
- data.csv, data.h5: Consolidated datasets
- Fake.csv, True.csv: Extended versions
- WELFake_Dataset.csv: 72,134 articles
- liar/: LIAR dataset (train.tsv, test.tsv, valid.tsv, README)

#### **logs/** (Experiment Logging)
- experiments.csv: Training run history with metrics

---

### Text Files & Documentation

#### **test_news_samples.txt** (Test Dataset)
- 5 labeled test articles:
  - SAMPLE 1: REAL - Federal Reserve article (Reuters style)
  - SAMPLE 2: FAKE - Medical misinformation (conspiracy style)
  - SAMPLE 3: REAL - Climate science article (BBC style)
  - SAMPLE 4: FAKE - Celebrity conspiracy (tabloid style)
  - SAMPLE 5: REAL - Space mission article (AP style)
- **Format**: Copy-paste ready for testing

#### **README.md** (Complete Documentation - 632 lines)
- Project overview and achievements
- Feature list with implementation details
- Installation and quick start guide
- Model performance metrics
- Usage instructions for all tabs
- API documentation and examples
- Database usage and troubleshooting
- Architecture overview
- Advanced model details and configuration

---

## ⚙️ Configuration Details

### Model Configuration (config.json)
```json
{
  "accuracy": 0.9646,
  "precision": 0.9584,
  "recall": 0.9714,
  "f1_score": 0.9648,
  "training_date": "2025-11-XX",
  "total_training_samples": 59220,
  "model_version": "2.0_advanced",
  "false_positive_rate": 0.01,
  "false_negative_rate": 0.002
}
```

### API Configuration
- **Gemini API**: 15 requests/minute free tier (1,500/day)
- **GNews API**: 100 requests/day free tier
- **Rate Limits** (FastAPI):
  - Single analysis: 30/minute
  - Batch analysis: 10/minute

### Text Processing Pipeline
1. Lowercase conversion
2. URL/email removal
3. HTML tag stripping
4. Special character removal (keep alphanumeric only)
5. Extra whitespace normalization
6. Lemmatization via spaCy
7. Stopword removal
8. Minimum 3-character word filtering

---

## 🔍 Feature Highlights

### ML Model (5-Algorithm Ensemble)
- **Soft Voting**: Averages probability predictions
- **8,000 TF-IDF Features** with trigrams (1-3)
- **Balanced Training**: 29,610 real + 29,610 fake samples
- **Hyperparameter Tuning**: GridSearchCV with StratifiedKFold CV

### Red Flag Detection
- Medical misinformation patterns
- Conspiracy theory indicators
- Clickbait phrases
- Urgency manipulation language
- Excessive punctuation detection
- Censorship claims

### Explainable AI Features
- Individual model voting breakdown
- Suspicious phrase highlighting with severity levels
- Word importance/TF-IDF visualization
- Topic classification
- Readability analysis
- Source reputation scoring

### Database Features
- SQLite persistence (analysis_history.db)
- 3 tables: analysis_history, user_feedback, source_reputation
- MD5-based article deduplication
- User rating collection for model improvement

---

## 🚀 How to Run

### Installation
```bash
cd "c:\Users\koush\OneDrive\Desktop\fake news detector"
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### Run Web Application
```bash
.venv\Scripts\python.exe -m streamlit run app.py
# Access at http://localhost:8501
```

### Run REST API
```bash
python api.py
# Access docs at http://localhost:8000/docs
```

### Retrain Model
```bash
python train.py
```

---

## 📊 Model Performance

| Metric | Score |
|--------|-------|
| Accuracy | **96.46%** |
| Precision | 95.84% |
| Recall | 97.14% |
| F1-Score | 96.48% |
| Validation (1,000 samples) | 97.10% |

---

## 🎯 Key Insights

1. **Production Ready**: All components integrated and tested
2. **Explainable**: Multiple visualization and analysis layers
3. **Scalable**: REST API for integration, batch processing support
4. **Learnable**: User feedback system for continuous improvement
5. **Multi-Source**: Combines ML, AI, and web verification for robust detection
6. **Well-Documented**: Comprehensive README, code comments, example tests

---

## 🔐 API Keys Required

1. **Google Gemini API**: https://ai.google.dev/
   - Current key in app.py: AIzaSyBa8Txd9gDph1tMP4h7A8iNkWiNN5UrQ3Q

2. **GNews API**: https://gnews.io/
   - Current key in app.py: 84750e988d2d3e69c1c5e94293393433

**⚠️ Security Note**: In production, use environment variables instead of hardcoded keys.

---

## 📝 Project Status

✅ **FULLY OPERATIONAL** - All components deployed and tested
- ML Model: Trained and validated
- APIs: Integrated and functional
- Database: Operational with history tracking
- UI: Responsive dashboard with 4 tabs
- Documentation: Complete and up-to-date

Generated: January 4, 2026
Last Update: Current session
