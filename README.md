# 🔍 Hybrid Fake News Detector

A production-ready machine learning system for detecting misinformation in news articles, powered by a robust Stacking Classifier ensemble, dynamic Out-Of-Distribution (OOD) detection, and automated model health monitoring.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Project Status](#project-status)
- [Installation](#installation)
- [Usage](#usage)
- [Evaluation & Monitoring](#evaluation--monitoring)
- [Model Performance](#model-performance)
- [File Structure](#file-structure)

---

## 📖 Overview

The **Hybrid Fake News Detector** is a state-of-the-art misinformation detection pipeline. Recently upgraded through a 6-Phase ML Improvement Plan, the system now features robust cross-domain generalization, meta-feature engineering, dynamic OOD scaling, and continuous production monitoring.

### System Layers

1. **ML Model Layer** - A robust Stacking Ensemble (LR+RF+SGD+SVC+LGBM) with a Meta-Learner, leveraging 15,000 TF-IDF features and 20 custom meta-features.
2. **AI Analysis Layer** - Google Gemini AI for credibility assessment and semantic verification.
3. **Web Verification Layer** - Real-time GNews API integration for cross-referencing and source corroboration.
4. **Monitoring Layer** - Automated model health tracking, OOD detection, and drift analysis.

---

## ✨ Key Features

### 🤖 Advanced Stacking Ensemble
- **Stacking Classifier** using 5 diverse base models:
  - Logistic Regression, SGD Classifier, LinearSVC, Random Forest, LightGBM.
- **Meta-Learner**: Logistic Regression to combine base predictions.
- **Calibrated Probabilities**: Isotonic regression for reliable confidence scores.

### 🧬 Rich Feature Engineering
- **TF-IDF Vectorization**: 15,000 top n-gram features.
- **Meta-Features**: 20 custom linguistic features (e.g., readability scores, sentiment polarity, subjectivity, keyword densities, red-flag indicators).
- **Standard Scaling**: Optimized scaling for numeric meta-features.

### 🌐 Cross-Domain Generalization
- Proven stability across distinct datasets (ISOT, WELFake, Kaggle, LIAR, FakeTrue).
- Automated cross-domain evaluation matrix to identify generalization gaps.

### 🛡️ Out-Of-Distribution (OOD) Detection
- Computes TF-IDF centroids during training to flag inputs that deviate significantly from the training distribution.
- **Dynamic Weighting**: Automatically reduces the ML model's influence and shifts weight to Gemini AI and Web Verification when encountering OOD articles.

### 🏥 Production Monitoring & Evaluation (Phase 6)
- **Model Monitor**: Tracks prediction drift, confidence distributions, and OOD frequencies via a SQLite database (`analysis_history.db`).
- **Health Alerts**: Automated alerts for high OOD rates, suspiciously high/low confidence, or skewed fake/real ratios.
- **Evaluation Reports**: Generates comprehensive PDF/JSON reports tracking phase-over-phase accuracy improvements.

---

## 🏗️ Architecture

```
Article Input
    │
    ├─► ML Pipeline
    │     ├── Text Cleaning & Feature Extraction (TF-IDF + 20 Meta-Features)
    │     ├── OOD Detection (Distance from Training Centroid)
    │     └── Stacking Ensemble Prediction (Base Models → Meta Learner)
    │
    ├─► AI Analysis Layer (Gemini)
    │
    └─► Web Verification Layer (GNews)
          │
          ▼
    Dynamic Weighting Engine
    (Shifts weight from ML to AI/Web if OOD Score is High)
          │
          ▼
    FINAL VERDICT & CONFIDENCE
    (Logged to Model Monitor for Health Tracking)
```

---

## ✅ Project Status: FULLY OPERATIONAL

| ML Improvement Phase | Status | Details |
|----------------------|--------|---------|
| **Phase 1**: Data Diversity | ✅ Complete | Synthetic OOD & Edge Case generation |
| **Phase 2**: Feature Eng. | ✅ Complete | Added 20 Meta-Features + Standard Scaling |
| **Phase 3**: Cross-Domain Eval| ✅ Complete | Automated cross-domain matrix generation |
| **Phase 4**: Optimization | ✅ Complete | Migrated to Stacking Ensemble + Calibration |
| **Phase 5**: Inference Pipeline| ✅ Complete | OOD Detection + Dynamic Weight Shifting |
| **Phase 6**: Monitoring | ✅ Complete | SQLite tracking, Health Alerts, Eval Reports |

---

## 🚀 Installation

### Prerequisites
- Python 3.10+
- At least 2GB RAM (for LightGBM and Spacy models)

### Setup
```bash
# Clone the repository and navigate to the directory
cd "fake news detector"

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### Configure APIs
Edit `app.py` or `.env` to configure your API keys:
```python
GEMINI_API_KEY = "your_gemini_key"  # https://ai.google.dev/
GNEWS_API_KEY = "your_gnews_key"    # https://gnews.io/
```

---

## 💻 Usage

### Web Dashboard
```bash
python -m streamlit run app.py
```
Access the application at **http://localhost:8501**.

### REST API
```bash
python api.py
```
Access API docs at **http://localhost:8000/docs**.

### Retrain the Model
To generate the Stacking Classifier and compute the OOD centroid:
```bash
python train.py
```

---

## 📊 Evaluation & Monitoring

### Generate Evaluation Report
You can generate a comprehensive JSON/Console report of the model's performance trajectory and current production health:
```bash
python eval_report.py
python eval_report.py --json
python eval_report.py --save  # Saves to logs/eval_report.json
```

### Monitor Tests
Run the monitoring test suite:
```bash
pytest tests/test_monitoring.py -v
```

---

## 📈 Model Performance

**Stacking (LR+RF+SGD+SVC+LGBM) + Meta, Calibrated (Phase 6)**

| Metric | Score |
|--------|-------|
| **Accuracy** | **94.74%** |
| Precision | 96.33% |
| Recall | 93.04% |
| F1-Score | 94.66% |
| ROC-AUC | 99.17% |

*Note: While accuracy is slightly adjusted from older overfit baselines, the model's cross-domain robustness and OOD resilience are significantly improved.*

---

## 📁 File Structure

```
fake news detector/
├── app.py                      # Main Streamlit web application
├── api.py                      # FastAPI REST API server
├── train.py                    # Stacking Classifier Training Script
├── ood_detector.py             # Out-of-Distribution scoring & dynamic weighting
├── model_monitor.py            # SQLite production health tracking
├── eval_report.py              # Performance report generator
├── database.py                 # Application history tracking
├── enhanced_features.py        # Meta-feature generation
├── utils.py                    # Core text cleaning & NLP utilities
├── cross_domain_eval.py        # Cross-dataset validation matrix
├── tests/
│   ├── test_model_quality.py   # Prediction assertions
│   └── test_monitoring.py      # Health monitor unit tests
├── models/                     # Trained models (model.joblib, scaler.joblib, tfidf.joblib, ood_centroid.npy)
└── logs/                       # Experiment histories and eval reports
```

---

**Status:** ✅ Production Ready  
**Model Version:** 5.0 (Phase 6)  
**Maintained by:** Hybrid Fake News Detector Team
