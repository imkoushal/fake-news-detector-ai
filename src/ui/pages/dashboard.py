"""
Dashboard page — analysis history, trends, and statistics.
"""

import streamlit as st
import pandas as pd

from src.core.logging_config import get_logger

logger = get_logger(__name__)


def render_dashboard_page(db):
    """Render the Dashboard tab."""
    if not db:
        st.warning("Database not available. Dashboard disabled.")
        return

    st.subheader("📊 Analysis History")
    stats = db.get_statistics()

    if stats["total"] == 0:
        st.info("No analysis history yet. Analyze some articles to see statistics!")
        return

    # Top metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Analyzed", stats["total"])
    with col2:
        st.metric("Avg Confidence", f"{stats['avg_confidence']:.1f}%")
    with col3:
        fake_count = stats["predictions"].get("FAKE", 0)
        fake_pct = (fake_count / stats["total"]) * 100
        st.metric("Fake Detected", f"{fake_count} ({fake_pct:.1f}%)")

    st.markdown("---")

    try:
        import plotly.express as px

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Real vs Fake")
            if stats["predictions"]:
                df_p = pd.DataFrame(list(stats["predictions"].items()), columns=["Label", "Count"])
                fig = px.pie(df_p, values="Count", names="Label", color="Label",
                             color_discrete_map={"REAL": "#00CC96", "FAKE": "#EF553B"})
                st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.subheader("Topics")
            if stats["categories"]:
                df_c = pd.DataFrame(list(stats["categories"].items()), columns=["Topic", "Count"])
                fig2 = px.bar(df_c, x="Topic", y="Count")
                st.plotly_chart(fig2, use_container_width=True)

        # Trend
        st.subheader("📈 Activity Trend")
        history = db.get_history(limit=500)
        if not history.empty and "timestamp" in history.columns:
            try:
                history["date"] = pd.to_datetime(history["timestamp"]).dt.date
                daily = history.groupby(["date", "prediction"]).size().reset_index(name="count")
                fig3 = px.line(daily, x="date", y="count", color="prediction",
                              title="Daily Volume", color_discrete_map={"REAL": "#00CC96", "FAKE": "#EF553B"}, markers=True)
                st.plotly_chart(fig3, use_container_width=True)
            except Exception:
                st.info("Not enough data for trend analysis yet.")
    except ImportError:
        st.info("Install plotly for charts: pip install plotly")

    # Recent history
    st.subheader("📜 Recent Analyses")
    history_df = db.get_history(limit=50)
    if not history_df.empty:
        display_cols = [c for c in ["timestamp", "prediction", "confidence", "category", "article_preview"] if c in history_df.columns]
        st.dataframe(history_df[display_cols], use_container_width=True)
        csv = history_df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download History", csv, "full_history.csv", "text/csv", key="dl-hist")

    # Top red flags
    if stats["top_red_flags"]:
        st.subheader("🚩 Top Suspicious Articles")
        for preview, score in stats["top_red_flags"]:
            st.warning(f"**Score {score:.2f}**: {preview[:150]}...")
