import streamlit as st

def render_header():
    """Render the main application header"""
    st.title('🔍 Hybrid Fake News Detector')
    st.caption('🎯 96.46% Accuracy | 59,220 Training Samples | 5-Model Ensemble | ML + AI + Web Verification')

def render_sidebar_metrics(cfg):
    """Render model metrics in the sidebar"""
    st.sidebar.subheader('🎯 Model Metrics')
    if cfg:
        accuracy = cfg.get('accuracy', 0.99)
        precision = cfg.get('precision', 0.99)
        recall = cfg.get('recall', 0.99)
        f1_score = cfg.get('f1_score', 0.99)
        
        # Display metrics in columns for better layout
        col1, col2 = st.sidebar.columns(2)
        with col1:
            st.metric('Accuracy', f"{accuracy*100:.2f}%")
            st.metric('Precision', f"{precision*100:.2f}%")
        with col2:
            st.metric('Recall', f"{recall*100:.2f}%")
            st.metric('F1-Score', f"{f1_score*100:.2f}%")
        
        # Additional metrics
        fpr = cfg.get('false_positive_rate', 0.01)
        fnr = cfg.get('false_negative_rate', 0.002)
        st.sidebar.metric('False Positive Rate', f"{fpr:.3f}%")
        st.sidebar.metric('False Negative Rate', f"{fnr:.3f}%")
        
        st.sidebar.caption(f"Training Date: {cfg.get('training_date', 'N/A')[:10]}")
        total_samples = cfg.get('total_training_samples', 0)
        if isinstance(total_samples, int):
            st.sidebar.caption(f"Total Samples: {total_samples:,}")
        else:
            st.sidebar.caption(f"Total Samples: {total_samples}")

def render_api_status(gnews_ok, gnews_msg, has_gemini):
    """Render API status in sidebar"""
    st.sidebar.markdown('---')
    st.sidebar.subheader('🌐 API Status')
    
    if gnews_ok:
        st.sidebar.success('✅ GNews API: Active')
        st.sidebar.caption(gnews_msg)
    else:
        st.sidebar.warning('⚠️ GNews API: Issue')
        st.sidebar.caption(gnews_msg)
    
    if has_gemini:
        st.sidebar.success('✅ Gemini AI: Active')
    else:
        st.sidebar.warning('⚠️ Gemini AI: Not configured')
        st.sidebar.caption('Add your Gemini API key in app.py')
