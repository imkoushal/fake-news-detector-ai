import streamlit as st
import json
import os
from joblib import load
import requests
import re
import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin

# Import new modules
from ui_components import render_header, render_sidebar_metrics, render_api_status
from state_management import init_session_state
from app_pages.analyze_page import render_analyze_page
from app_pages.batch_page import render_batch_page
from app_pages.dashboard_page import render_dashboard_page
from api_client import check_gnews_api, gemini_verify_claim, search_news_gnews, translate_text

# Import utils and features
try:
    from utils import clean_text, extract_features, get_conspiracy_indicators, get_sensationalism_score
except ImportError:
    st.error("❌ Critical Error: utils.py not found. Please ensure all files are present.")
    st.stop()

# Configuration
MODEL_PATH = 'models/pipeline.joblib'
CONFIG_PATH = 'models/config.json'
# NOTE: In production, use st.secrets or environment variables
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Initialize optional features
try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

try:
    from database import AnalysisDatabase
    from enhanced_features import (
        analyze_source, classify_topic, get_word_importance,
        get_model_predictions, highlight_suspicious_phrases,
        calculate_readability_score, extract_time_references,
        extract_domain
    )
    db = AnalysisDatabase()
    HAS_ENHANCED_FEATURES = True
except Exception as e:
    HAS_ENHANCED_FEATURES = False
    db = None

# --- Helper Functions ---

class FinalModel(BaseEstimator, ClassifierMixin):
    def __init__(self, vectorizer, model):
        self.vectorizer = vectorizer
        self.model = model
    
    def predict(self, X):
        X_tfidf = self.vectorizer.transform(X)
        return self.model.predict(X_tfidf)
    
    def predict_proba(self, X):
        X_tfidf = self.vectorizer.transform(X)
        return self.model.predict_proba(X_tfidf)

@st.cache_resource
def load_model():
    try:
        # Try loading newest model format (model.joblib + tfidf.joblib)
        if os.path.exists('models/model.joblib') and os.path.exists('models/tfidf.joblib'):
            vectorizer = load('models/tfidf.joblib')
            model = load('models/model.joblib')
            pipe = FinalModel(vectorizer=vectorizer, model=model)
            
            if os.path.exists('models/config.json'):
                with open('models/config.json') as f:
                    config = json.load(f)
            else:
                config = {}
            return pipe, 0.5, config
            
        # Fallback to optimized model
        elif os.path.exists('models/pipeline_optimized.joblib'):
            model_data = load('models/pipeline_optimized.joblib')
            if isinstance(model_data, dict) and 'vectorizer' in model_data:
                pipe = FinalModel(
                    vectorizer=model_data['vectorizer'],
                    model=model_data['model']
                )
            else:
                pipe = model_data
            
            if os.path.exists('models/config.json'):
                with open('models/config.json') as f:
                    config = json.load(f)
            else:
                config = {}
            return pipe, 0.5, config
            
        elif os.path.exists(MODEL_PATH):
            pipe = load(MODEL_PATH)
            with open(CONFIG_PATH) as f:
                config = json.load(f)
            return pipe, 0.5, config
        else:
            return None, 0.5, {}
            
    except Exception as e:
        st.error(f"❌ Error loading model: {str(e)}")
        return None, 0.5, {}

# --- Main Application ---

st.set_page_config(
    page_title='Hybrid Fake News Detector', 
    page_icon='🔍', 
    layout='wide',
    initial_sidebar_state='expanded',
    menu_items={
        'Get Help': 'https://github.com/your-repo',
        'Report a bug': 'https://github.com/your-repo/issues',
        'About': '# Hybrid Fake News Detector v2.0\nMLinformation detection with 96.46% accuracy'
    }
)

# Initialize state
init_session_state()

# Dark mode toggle
dark_mode = st.sidebar.checkbox('🌙 Dark Mode', value=False)
if dark_mode:
    st.markdown("""
    <style>
        .stApp {
            background-color: #0E1117;
            color: #FAFAFA;
        }
        .stTextArea textarea {
            background-color: #262730;
            color: #FAFAFA;
        }
    </style>
    """, unsafe_allow_html=True)

# Render Header
render_header()

# Load Model
pipe, threshold, cfg = load_model()

# Sidebar
with st.sidebar:
    render_sidebar_metrics(cfg)
    
    # Check API status
    ok, msg, details = check_gnews_api(GNEWS_API_KEY)
    render_api_status(ok, msg, HAS_GEMINI)
    
    st.markdown('---')
    st.subheader('⚙️ Settings')
    sensitivity = st.slider('Detection Sensitivity', 0.0, 1.0, threshold, 0.05)
    st.caption('Lower = more likely to flag as fake')
    
    if HAS_ENHANCED_FEATURES and db:
        st.markdown('---')
        if st.button('📜 View History', use_container_width=True):
            st.session_state['show_history'] = True

# Main Tabs
tab1, tab2, tab3, tab4 = st.tabs(['🔍 Analyze', '📦 Batch Upload', 'ℹ️ Info', '📊 Dashboard'])

with tab1:
    # Pass API keys implicitly via bound functions or explicit args
    # We'll wrap the API calls to include keys
    verify_func = lambda text: gemini_verify_claim(text, GEMINI_API_KEY)
    search_func = lambda query, max_results=10: search_news_gnews(query, GNEWS_API_KEY, max_results)
    translate_func = lambda text: translate_text(text, 'en', GEMINI_API_KEY)
    
    render_analyze_page(pipe, sensitivity, db, HAS_ENHANCED_FEATURES, verify_func, search_func, translate_func)

with tab2:
    render_batch_page(pipe, db)

with tab3:
    st.markdown("""
    ### About
    This Hybrid Fake News Detector uses a 5-model ensemble (Logistic Regression, Random Forest, etc.) trained on 59,000+ articles.
    
    It combines:
    1. **ML Analysis**: Statistical text analysis
    2. **AI Verification**: Google Gemini AI for logic and fact-checking
    3. **Web Search**: Real-time cross-referencing with GNews
    
    ### How to use
    - Paste a full article in the **Analyze** tab
    - Upload a CSV in the **Batch Upload** tab
    - View statistics in the **Dashboard** tab
    """)

with tab4:
    render_dashboard_page(db)
