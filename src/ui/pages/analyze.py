"""
Analyze page — the core analysis tab with ML + Gemini + Web verification.

Rewritten to use src.* modules, proper error handling, OOD detection,
and structured logging throughout.
"""

import streamlit as st
import pandas as pd
from collections import Counter

from src.core.logging_config import get_logger, set_correlation_id
from src.core.validators import validate_article_text, check_article_quality
from src.core.exceptions import ValidationError
from src.core.metrics import metrics
from src.ml.preprocessing import clean_text, extract_keywords
from src.ml.features import (
    extract_features, get_conspiracy_indicators, get_sensationalism_score,
    classify_topic, highlight_suspicious_phrases, calculate_readability_score,
    detect_fake_news_red_flags, extract_domain, analyze_source,
)
from src.ml.ood_detector import ood_detector
from src.ml.model_monitor import model_monitor

logger = get_logger(__name__)


def render_analyze_page(pipe, sensitivity, db, gemini_client, gnews_client):
    """Render the Analyze tab."""
    st.subheader("Enter Article")
    st.info("ℹ️ **Best Results:** Paste the complete article text (500-1000+ characters).")

    text = st.text_area("Paste:", height=250, placeholder="Enter or paste the full article text here...")

    # Translation option
    enable_translation = st.checkbox(
        "🌐 Input is not English (Auto-translate to English)",
        help="Uses Gemini AI to translate text before analysis",
    )

    # Quality indicator
    if text.strip():
        quality = check_article_quality(text.strip())
        if quality["quality_warning"]:
            st.warning(f"⚠️ {quality['quality_warning']}")
        else:
            st.success(f"✓ {quality['char_count']} characters, {quality['word_count']} words")

    if st.button("🔍 Analyze", use_container_width=True):
        if not pipe or not pipe.is_loaded:
            st.error("❌ Model not loaded. Please check model files or retrain.")
            return
        if not text.strip():
            st.warning("⚠️ Please enter some text to analyze.")
            return

        # Generate correlation ID for this analysis
        cid = set_correlation_id()
        logger.info("Analysis started", extra={"article_length": len(text), "request_id": cid})

        try:
            validated_text = validate_article_text(text, min_length=50)
        except ValidationError as e:
            st.error(f"❌ {e}")
            return

        with st.spinner("Analyzing..."):
            # Translation
            if enable_translation and gemini_client.is_available:
                with st.status("Translating text...", expanded=True) as status:
                    translated = gemini_client.translate_text(validated_text)
                    if translated and translated != validated_text:
                        st.write("Translation complete!")
                        with st.expander("View Translated Text"):
                            st.write(translated)
                        validated_text = translated
                        status.update(label="Translation Complete", state="complete", expanded=False)
                    else:
                        status.update(label="Translation failed (using original)", state="error")

            cleaned = clean_text(validated_text)
            if len(cleaned.strip()) < 5:
                st.warning("⚠️ Text contains no analyzable content after cleaning.")
                return

            # --- ML Prediction ---
            result = pipe.analyze(cleaned)
            real_prob = result["real_probability"]
            fake_prob = result["fake_probability"]

            # --- Red flags ---
            red_flag_score = detect_fake_news_red_flags(validated_text)

            # --- OOD Detection ---
            ood_result = ood_detector.check(
                validated_text, cleaned, pipe.vectorizer, 
                pipe.predict_proba([cleaned])[0]
            )

            # ML prediction — show the actual model output, not OOD-adjusted
            pred = "REAL" if real_prob >= sensitivity else "FAKE"
            conf = max(real_prob, fake_prob) * 100

            # Keep OOD-adjusted score for internal hybrid calculation only
            adjusted_real_prob = real_prob * (1 - red_flag_score * 0.3)
            if ood_result["is_ood"]:
                adjusted_real_prob *= ood_result["confidence_adjustment"]

            # --- Display results ---
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Prediction", f"{'🟢 REAL' if pred == 'REAL' else '🔴 FAKE'}")
            with col2:
                st.metric("Confidence", f"{conf:.1f}%")
            with col3:
                st.metric("Real Score", f"{real_prob:.3f}")

            # OOD warning
            if ood_result["is_ood"]:
                st.warning("⚠️ **Out-of-Distribution Warning:** " + "; ".join(ood_result["reasons"]))

            # Red flags
            if red_flag_score > 0.3:
                st.error(f"🚩 **RED FLAGS DETECTED:** {red_flag_score*100:.0f}%")

            # Features
            features = extract_features(validated_text)
            conspiracy = get_conspiracy_indicators(validated_text)
            sensationalism = get_sensationalism_score(validated_text)

            c1, c2, c3, c4 = st.columns(4)
            with c1: st.metric("Sentences", features["sentence_count"])
            with c2: st.metric("Questions", features["question_count"])
            with c3: st.metric("Exclamations", features["exclamation_count"])
            with c4: st.metric("Avg Length", f"{features['avg_sentence_length']:.1f}")

            if conspiracy > 0:
                st.warning(f"⚠️ Conspiracy indicators: {conspiracy}")
            if sensationalism > 0.3:
                st.warning(f"⚠️ Sensationalism score: {sensationalism:.3f}")

            st.markdown("---")

            # --- Visualizations ---
            st.subheader("📊 Content Analysis")
            try:
                import plotly.express as px
                v1, v2 = st.columns(2)
                with v1:
                    words = [w.lower() for w in cleaned.split() if len(w) > 3]
                    wc = Counter(words).most_common(10)
                    if wc:
                        df_w = pd.DataFrame(wc, columns=["Word", "Count"])
                        fig = px.bar(df_w, x="Count", y="Word", orientation="h", title="Top 10 Words", color="Count", color_continuous_scale="Viridis")
                        fig.update_layout(yaxis={"categoryorder": "total ascending"})
                        st.plotly_chart(fig, use_container_width=True)
                with v2:
                    sents = [len(s.split()) for s in validated_text.split(".") if s.strip()]
                    if sents:
                        fig2 = px.histogram(x=sents, nbins=10, title="Sentence Length Distribution", labels={"x": "Words per Sentence", "y": "Count"})
                        st.plotly_chart(fig2, use_container_width=True)
            except ImportError:
                st.info("Install plotly for visualizations: pip install plotly")

            st.markdown("---")

            # --- Explainability ---
            st.subheader("🧠 Explainable AI")

            with st.expander("🤖 Individual Model Predictions", expanded=False):
                try:
                    preds = pipe.get_individual_predictions(pipe.vectorizer.transform([cleaned]))
                    if preds:
                        cols = st.columns(min(len(preds), 5))
                        for i, (name, info) in enumerate(preds.items()):
                            with cols[i % len(cols)]:
                                st.metric(name, info["prediction"], f"{info['confidence']:.1f}%")
                    else:
                        st.info("Individual predictions not available")
                except Exception:
                    st.info("Model breakdown not available for this model type")

            with st.expander("🚩 Suspicious Phrases", expanded=False):
                suspicious = highlight_suspicious_phrases(validated_text)
                if suspicious:
                    severity_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}
                    for f in suspicious[:10]:
                        st.markdown(f"{severity_icon.get(f['severity'], '⚪')} **{f['category']}**: \"{f['text']}\"")
                else:
                    st.success("✅ No major suspicious phrases detected")

            topic, topic_conf = classify_topic(validated_text)
            st.info(f"📂 **Detected Topic:** {topic.title()} (confidence: {topic_conf*100:.0f}%)")

            readability = calculate_readability_score(validated_text)
            r1, r2 = st.columns(2)
            with r1: st.metric("Reading Level", f"Grade {readability['grade_level']}")
            with r2: st.metric("Difficulty", readability["difficulty"])

            domain = extract_domain(validated_text)
            if domain:
                src = analyze_source(domain)
                if src["category"] == "trusted":
                    st.success(f"✅ **Source:** {domain} — Trusted ({src['reputation']}%)")
                elif src["category"] == "unreliable":
                    st.error(f"❌ **Source:** {domain} — Unreliable ({src['reputation']}%)")
                else:
                    st.warning(f"⚠️ **Source:** {domain} — Unknown ({src['reputation']}%)")

            st.markdown("---")

            # --- Save to DB ---
            article_hash = None
            if db:
                try:
                    article_hash = db.add_analysis(
                        article_text=validated_text, prediction=pred, confidence=conf,
                        real_prob=real_prob, fake_prob=fake_prob, red_flag_score=red_flag_score,
                        ood_score=1.0 - ood_result["confidence_adjustment"],
                        model_version=result.get("model_version", ""),
                        source_domain=domain, category=topic,
                    )
                except Exception as e:
                    logger.error(f"Failed to save analysis to database: {e}", exc_info=True)
                    st.warning("⚠️ Could not save to history database.")

            # --- User feedback ---
            if article_hash and db:
                st.markdown("---")
                st.subheader("📝 Rate This Analysis")
                fc1, fc2 = st.columns([3, 1])
                with fc1:
                    rating = st.select_slider(
                        "Was this prediction accurate?", options=[1, 2, 3, 4, 5], value=3,
                        format_func=lambda x: ["❌ Wrong", "⚠️ Poor", "😐 OK", "👍 Good", "✅ Perfect"][x-1],
                        key=f"rating_{article_hash}",
                    )
                with fc2:
                    if st.button("Submit Rating", key=f"submit_{article_hash}"):
                        try:
                            db.add_feedback(article_hash, rating)
                            st.success("✓ Thanks for your feedback!")
                        except Exception as e:
                            logger.error(f"Failed to save feedback: {e}")
                            st.error("Could not save feedback.")

            st.markdown("---")

            # --- Gemini AI ---
            st.subheader("🤖 Gemini AI Credibility Check")
            gemini_result = None
            gemini_score = 0.5
            if gemini_client.is_available:
                with st.spinner("🧠 Gemini AI is performing fact-checking..."):
                    try:
                        gemini_result = gemini_client.verify_claim(validated_text)
                        if gemini_result:
                            st.success("✅ Gemini AI Analysis Complete")
                            st.info(gemini_result)
                            gemini_score = gemini_client.parse_verdict(gemini_result)
                    except Exception as e:
                        st.warning(f"⚠️ Gemini AI error: {e}")
            else:
                st.warning("⚠️ Gemini AI not configured. Set GEMINI_API_KEY in .env")

            # --- Web Search ---
            st.subheader("🌐 Web Verification")
            keywords = extract_keywords(validated_text)
            articles = []
            if keywords and gnews_client.is_configured:
                with st.spinner("🔍 Searching news sources..."):
                    articles = gnews_client.search(keywords, max_results=10)
                    if articles:
                        st.success(f"✅ Found {len(articles)} related articles")
                        rows = [{"Source": a.get("source", {}).get("name", "?"), "Headline": a.get("title", "")[:120], "Date": a.get("publishedAt", "?")} for a in articles]
                        st.table(pd.DataFrame(rows))
                        with st.expander("📰 View Full Articles", expanded=False):
                            for a in articles[:5]:
                                st.markdown(f"**[{a.get('title', 'No title')}]({a.get('url', '#')})**")
                                st.caption(f"Source: {a.get('source', {}).get('name', '?')} | {a.get('publishedAt', '?')}")
                                if a.get("description"):
                                    st.write(a["description"][:200] + "...")
                                st.markdown("---")
                    else:
                        st.warning("⚠️ No related articles found.")
            elif not gnews_client.is_configured:
                st.warning("⚠️ GNews not configured. Set GNEWS_API_KEY in .env")

            web_score = gnews_client.calculate_web_score(articles, bool(keywords))

            st.markdown("---")

            # --- FINAL VERDICT ---
            st.subheader("⚖️ FINAL VERDICT (Hybrid Analysis)")
            ml_score = real_prob

            # Determine effective scores — use neutral (0.5) for API failures
            effective_gemini = gemini_score if gemini_result else 0.5
            effective_web = web_score

            # Adaptive weighting: ML model is the primary signal
            # When Gemini actually ran, give it weight; otherwise it's neutral
            ml_weight = 0.60
            gemini_weight = 0.25 if gemini_result else 0.0
            web_weight = 0.15 if articles else 0.0
            # Redistribute unused weight to ML
            unused_weight = 1.0 - ml_weight - gemini_weight - web_weight
            ml_weight += unused_weight

            final_score = (ml_score * ml_weight) + (effective_gemini * gemini_weight) + (effective_web * web_weight)
            if red_flag_score > 0.3:
                final_score *= (1 - red_flag_score * 0.5)

            # Record monitoring data
            ml_agrees = (pred == "REAL") == (gemini_score > 0.5)
            model_monitor.record(pred, conf, ml_agrees)

            # Confidence calculation
            if final_score >= 0.58:
                final_conf = (final_score - 0.5) * 200
            elif final_score <= 0.38:
                final_conf = (0.5 - final_score) * 200
            else:
                final_conf = abs(final_score - 0.5) * 60

            v1, v2, v3 = st.columns(3)
            with v1: st.metric("ML Model", "REAL" if ml_score > 0.5 else "FAKE", f"{ml_score*100:.0f}%")
            with v2: st.metric("Gemini AI", "REAL" if gemini_score > 0.5 else "FAKE", f"{gemini_score*100:.0f}%")
            with v3: st.metric("Web Verify", "REAL" if web_score > 0.5 else "FAKE", f"{len(articles)} articles" if articles else "No articles")

            st.markdown("---")

            if final_score >= 0.58:
                st.success(f"### ✅ FINAL VERDICT: LIKELY REAL\n**Confidence: {final_conf:.1f}%**")
            elif final_score <= 0.38:
                st.error(f"### ❌ FINAL VERDICT: LIKELY FAKE\n**Confidence: {final_conf:.1f}%**")
            else:
                st.warning(f"### ⚠️ FINAL VERDICT: UNCERTAIN\n**Confidence: {final_conf:.1f}%** — Manual fact-checking recommended")

            with st.expander("📊 Detailed Breakdown"):
                st.write(f"**ML Score:** {ml_score:.3f} ({ml_weight*100:.0f}%)  |  **Gemini:** {effective_gemini:.3f} ({gemini_weight*100:.0f}%)  |  **Web:** {effective_web:.3f} ({web_weight*100:.0f}%)")
                st.write(f"**Red Flags:** {red_flag_score:.3f}  |  **Final:** {final_score:.3f}")
                if ood_result["is_ood"]:
                    st.write(f"**OOD Adjustment:** {ood_result['confidence_adjustment']:.2f}x")

            # Update DB with final scores
            if article_hash and db:
                try:
                    db.add_analysis(
                        article_text=validated_text, prediction=pred, confidence=conf,
                        real_prob=real_prob, fake_prob=fake_prob, red_flag_score=red_flag_score,
                        gemini_verdict=gemini_result[:500] if gemini_result else None,
                        web_score=web_score, final_score=final_score,
                        source_domain=domain, category=topic,
                        model_version=result.get("model_version", ""),
                    )
                except Exception as e:
                    logger.debug(f"Final DB update failed: {e}")

            logger.info("Analysis complete", extra={
                "prediction": pred, "confidence": round(conf, 1),
                "final_score": round(final_score, 3), "request_id": cid,
            })
