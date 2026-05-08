"""
Streamlit Application Entry Point — Industry-Grade Fake News Detector v3.0

Run with: streamlit run streamlit_app.py
"""

import streamlit as st

from src.core.config import settings
from src.core.logging_config import get_logger
from src.ml.model import load_model
from src.ml.ood_detector import ood_detector
from src.db.database import AnalysisDatabase
from src.external.gemini_client import GeminiClient
from src.external.gnews_client import GNewsClient
from src.ui.components import render_header, render_sidebar_metrics, render_api_status
from src.ui.state import init_session_state
from src.ui.pages.analyze import render_analyze_page
from src.ui.pages.batch import render_batch_page
from src.ui.pages.dashboard import render_dashboard_page

logger = get_logger(__name__)

# --- Page config ---
st.set_page_config(
    page_title="Hybrid Fake News Detector",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com/your-repo",
        "Report a bug": "https://github.com/your-repo/issues",
        "About": "# Hybrid Fake News Detector v3.0\nIndustry-grade ML fake news detection",
    },
)

# --- Initialize state ---
init_session_state()

# --- Dark mode ---
dark_mode = st.sidebar.checkbox("🌙 Dark Mode", value=False)
if dark_mode:
    st.markdown("""<style>
        .stApp { background-color: #0E1117; color: #FAFAFA; }
        .stTextArea textarea { background-color: #262730; color: #FAFAFA; }
    </style>""", unsafe_allow_html=True)

# --- Header ---
render_header()

# --- Load model (cached) ---
@st.cache_resource
def _load_model():
    try:
        model = load_model()
        # Configure OOD detector with the model's vectorizer
        ood_detector.configure(model.vectorizer)
        return model
    except Exception as e:
        logger.error(f"Model load failed: {e}")
        st.error(f"❌ Error loading model: {e}")
        return None

pipe = _load_model()

# --- Initialize services ---
@st.cache_resource
def _init_services():
    db = AnalysisDatabase()
    gemini = GeminiClient()
    gnews = GNewsClient()
    return db, gemini, gnews

db, gemini_client, gnews_client = _init_services()

# --- Sidebar ---
with st.sidebar:
    if pipe:
        render_sidebar_metrics(pipe.config)
    else:
        st.warning("Model not loaded")

    # API status (uses cached GNews check — no longer calls on every page load)
    ok, msg, _ = gnews_client.check_status()
    render_api_status(ok, msg, gemini_client.is_available)

    st.markdown("---")
    st.subheader("⚙️ Settings")
    threshold = pipe.config.get("threshold", 0.5) if pipe else 0.5
    sensitivity = st.slider("Detection Sensitivity", 0.0, 1.0, threshold, 0.05)
    st.caption("Lower = more likely to flag as fake")

    if db:
        st.markdown("---")
        if st.button("📜 View History", use_container_width=True):
            st.session_state["show_history"] = True

# --- Main Tabs ---
tab1, tab2, tab3, tab4 = st.tabs(["🔍 Analyze", "📦 Batch Upload", "ℹ️ Info", "📊 Dashboard"])

with tab1:
    render_analyze_page(pipe, sensitivity, db, gemini_client, gnews_client)

with tab2:
    render_batch_page(pipe, db)

with tab3:
    st.markdown("""
    ### About
    This Hybrid Fake News Detector uses a 5-model ensemble (Logistic Regression, Random Forest, etc.) trained on 59,000+ articles.
    
    It combines:
    1. **ML Analysis**: Statistical text analysis with TF-IDF + ensemble models
    2. **AI Verification**: Google Gemini AI for logic and fact-checking
    3. **Web Search**: Real-time cross-referencing with GNews
    4. **OOD Detection**: Warns when input is outside the model's training domain
    
    ### How to use
    - Paste a full article in the **Analyze** tab
    - Upload a CSV in the **Batch Upload** tab
    - View statistics in the **Dashboard** tab
    
    ### Configuration
    - Copy `.env.example` to `.env` and add your API keys
    - Never commit `.env` to version control
    """)

with tab4:
    render_dashboard_page(db)
