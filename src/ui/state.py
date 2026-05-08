"""Session state management for Streamlit."""

import streamlit as st


def init_session_state():
    """Initialize all session state variables with defaults."""
    defaults = {
        "show_history": False,
        "analysis_results": None,
        "last_article_hash": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def get_state(key, default=None):
    return st.session_state.get(key, default)


def set_state(key, value):
    st.session_state[key] = value
