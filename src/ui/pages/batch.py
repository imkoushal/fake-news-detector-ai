"""
Batch processing page — rewritten with proper validation and error reporting.
"""

import streamlit as st
import pandas as pd

from src.core.logging_config import get_logger
from src.core.validators import validate_csv_upload
from src.core.exceptions import ValidationError
from src.ml.preprocessing import clean_text
from src.ml.features import detect_fake_news_red_flags

logger = get_logger(__name__)


def render_batch_page(pipe, db):
    """Render the Batch Upload tab."""
    st.subheader("📦 Bulk Analysis")

    uploaded_file = st.file_uploader(
        "Upload CSV file (must have a 'text' or 'content' column)",
        type=["csv"],
    )

    if uploaded_file is None:
        return

    try:
        df = pd.read_csv(uploaded_file)
        df, text_col = validate_csv_upload(df, max_rows=500)
        st.success(f"Found text column: '{text_col}' — {len(df)} valid rows")
    except ValidationError as e:
        st.error(f"❌ {e}")
        return
    except Exception as e:
        st.error(f"❌ Error reading file: {e}")
        return

    if not st.button("Start Batch Analysis"):
        return

    if not pipe or not pipe.is_loaded:
        st.error("❌ Model not loaded.")
        return

    results = []
    errors = []
    progress = st.progress(0)

    for i, row in df.iterrows():
        text = str(row[text_col])
        idx = i + 1
        try:
            if len(text.strip()) < 50:
                errors.append({"row": idx, "error": "Text too short"})
                continue

            cleaned = clean_text(text)
            result = pipe.analyze(cleaned)
            red_flags = detect_fake_news_red_flags(text)

            results.append({
                "text_preview": text[:100] + "...",
                "prediction": result["prediction"],
                "confidence": f"{result['confidence']:.1f}%",
                "real_prob": round(result["real_probability"], 3),
                "fake_prob": round(result["fake_probability"], 3),
                "red_flags": round(red_flags, 2),
            })

            # Save to DB
            if db:
                try:
                    db.add_analysis(
                        article_text=text, prediction=result["prediction"],
                        confidence=result["confidence"],
                        real_prob=result["real_probability"],
                        fake_prob=result["fake_probability"],
                        red_flag_score=red_flags,
                        model_version=result.get("model_version", ""),
                    )
                except Exception as e:
                    logger.warning(f"Batch DB save failed for row {idx}: {e}")

        except Exception as e:
            errors.append({"row": idx, "error": str(e)})
            logger.error(f"Batch processing error for row {idx}: {e}")

        progress.progress(idx / len(df))

    # Display results
    if results:
        results_df = pd.DataFrame(results)
        st.dataframe(results_df, use_container_width=True)

        # Summary
        fake_count = sum(1 for r in results if r["prediction"] == "FAKE")
        st.info(f"**Summary:** {len(results)} processed — {fake_count} FAKE, {len(results) - fake_count} REAL")

        # Download
        csv = results_df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download Results CSV", csv, "analysis_results.csv", "text/csv")

    # Display errors
    if errors:
        st.warning(f"⚠️ {len(errors)} rows failed:")
        st.dataframe(pd.DataFrame(errors), use_container_width=True)

    logger.info(f"Batch complete: {len(results)} succeeded, {len(errors)} failed",
                extra={"batch_size": len(df)})
