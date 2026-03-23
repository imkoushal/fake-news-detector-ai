import streamlit as st

def init_session_state():
    """Initialize session state variables"""
    if 'show_history' not in st.session_state:
        st.session_state['show_history'] = False
    
    if 'analysis_results' not in st.session_state:
        st.session_state['analysis_results'] = None

def get_state(key, default=None):
    """Get a value from session state"""
    return st.session_state.get(key, default)

def set_state(key, value):
    """Set a value in session state"""
    st.session_state[key] = value
