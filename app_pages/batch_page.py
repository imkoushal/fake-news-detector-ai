import streamlit as st
import pandas as pd
from utils import clean_text

def render_batch_page(pipe, db):
    """Render the Batch Upload tab"""
    st.subheader('Bulk Analysis')
    
    uploaded_file = st.file_uploader("Upload CSV file (must have a 'text' or 'content' column)", type=['csv'])
    
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            text_col = None
            for col in ['text', 'content', 'article', 'body']:
                if col in df.columns:
                    text_col = col
                    break
            
            if text_col:
                st.success(f"Found text column: '{text_col}' - {len(df)} rows")
                
                if st.button('Start Batch Analysis'):
                    results = []
                    progress_bar = st.progress(0)
                    
                    for i, row in df.iterrows():
                        text = str(row[text_col])
                        if len(text) > 50:
                            cleaned = clean_text(text)
                            proba = pipe.predict_proba([cleaned], raw_texts=[text])[0]
                            pred = 'FAKE' if proba[1] > 0.5 else 'REAL'
                            conf = max(proba) * 100
                            
                            results.append({
                                'text_preview': text[:100] + '...',
                                'prediction': pred,
                                'confidence': f"{conf:.1f}%",
                                'real_prob': proba[0],
                                'fake_prob': proba[1]
                            })
                            
                            # Save to DB if available
                            if db:
                                try:
                                    db.add_analysis(
                                        article_text=text,
                                        prediction=pred,
                                        confidence=conf,
                                        real_prob=proba[0],
                                        fake_prob=proba[1],
                                        red_flag_score=0.0 # Batch doesn't do deep analysis for speed
                                    )
                                except:
                                    pass
                        
                        progress_bar.progress((i + 1) / len(df))
                    
                    results_df = pd.DataFrame(results)
                    st.dataframe(results_df)
                    
                    # Download button
                    csv = results_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "Download Results CSV",
                        csv,
                        "analysis_results.csv",
                        "text/csv",
                        key='download-csv'
                    )
            else:
                st.error("Could not find a suitable text column. Please ensure your CSV has a 'text', 'content', or 'body' column.")
        except Exception as e:
            st.error(f"Error reading file: {e}")
