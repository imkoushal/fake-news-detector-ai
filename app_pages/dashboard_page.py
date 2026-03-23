import streamlit as st
import plotly.express as px
import pandas as pd

def render_dashboard_page(db):
    """Render the Dashboard tab"""
    if not db:
        st.warning("Database not available. Dashboard disabled.")
        return

    st.subheader('📊 Analysis History')
    stats = db.get_statistics()
    
    if stats['total'] > 0:
        # Top metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric('Total Analyzed', stats['total'])
        with col2:
            st.metric('Avg Confidence', f"{stats['avg_confidence']:.1f}%")
        with col3:
            fake_count = stats['predictions'].get('FAKE', 0)
            fake_pct = (fake_count / stats['total']) * 100
            st.metric('Fake News Detected', f"{fake_count} ({fake_pct:.1f}%)")
        
        st.markdown('---')
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader('Real vs Fake Distribution')
            if stats['predictions']:
                df_pred = pd.DataFrame(list(stats['predictions'].items()), columns=['Label', 'Count'])
                fig = px.pie(df_pred, values='Count', names='Label', color='Label',
                             color_discrete_map={'REAL': '#00CC96', 'FAKE': '#EF553B'})
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader('Topic Distribution')
            if stats['categories']:
                df_cat = pd.DataFrame(list(stats['categories'].items()), columns=['Topic', 'Count'])
                fig = px.bar(df_cat, x='Topic', y='Count')
                st.plotly_chart(fig, use_container_width=True)
        
        # Trend Analysis
        st.subheader('📈 Activity Trend')
        history_all = db.get_history(limit=500)
        if not history_all.empty and 'timestamp' in history_all.columns:
            try:
                history_all['date'] = pd.to_datetime(history_all['timestamp']).dt.date
                daily_counts = history_all.groupby(['date', 'prediction']).size().reset_index(name='count')
                
                fig_trend = px.line(daily_counts, x='date', y='count', color='prediction',
                                  title='Daily Analysis Volume by Verdict',
                                  color_discrete_map={'REAL': '#00CC96', 'FAKE': '#EF553B'},
                                  markers=True)
                st.plotly_chart(fig_trend, use_container_width=True)
            except Exception as e:
                st.info(f"Not enough data for trend analysis yet.")

        # Recent History Table
        st.subheader('📜 Recent Analyses')
        history_df = db.get_history(limit=50)
        if not history_df.empty:
            st.dataframe(
                history_df[['timestamp', 'prediction', 'confidence', 'category', 'article_preview']],
                use_container_width=True
            )
            
            # CSV Download
            csv = history_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "Download Full History CSV",
                csv,
                "full_history.csv",
                "text/csv",
                key='download-history'
            )
        
        # Top Red Flags
        if stats['top_red_flags']:
            st.subheader('🚩 Top Suspicious Articles')
            for preview, score in stats['top_red_flags']:
                st.warning(f"**Score {score:.2f}**: {preview[:150]}...")
                
    else:
        st.info('No analysis history yet. Analyze some articles to see statistics!')
