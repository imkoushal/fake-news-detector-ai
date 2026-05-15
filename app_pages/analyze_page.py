import streamlit as st
import pandas as pd
from utils import clean_text, extract_features, get_conspiracy_indicators, get_sensationalism_score, extract_keywords
from enhanced_features import (
    analyze_source, classify_topic, get_model_predictions, highlight_suspicious_phrases,
    calculate_readability_score, extract_domain, detect_fake_news_red_flags
)
try:
    from ood_detector import get_dynamic_weights, calibrate_confidence
    HAS_OOD = True
except ImportError:
    HAS_OOD = False
try:
    from model_monitor import ModelMonitor
    _monitor = ModelMonitor()
    HAS_MONITOR = True
except ImportError:
    HAS_MONITOR = False

def render_analyze_page(pipe, sensitivity, db, has_enhanced_features, gemini_verify_claim, search_news_gnews, translate_text=None):
    """Render the Analyze tab"""
    st.subheader('Enter Article')
    
    st.info("ℹ️ **Best Results:** Paste the complete article text (at least 500-1000 characters). Short summaries may not be analyzed accurately since the model was trained on full-length news articles.")
    
    text = st.text_area('Paste:', height=250, placeholder="Enter or paste the full article text here...")
    
    # Translation option
    enable_translation = st.checkbox("🌐 Input is not English (Auto-translate to English)", help="Uses Gemini AI to translate text before analysis")
    
    # Character count
    char_count = len(text.strip())
    if char_count > 0:
        if char_count < 500:
            st.warning(f"⚠️ Current length: {char_count} characters. Article may be too short for accurate analysis (recommended: 500+ chars)")
        else:
            st.success(f"✓ Current length: {char_count} characters")
    
    if st.button('🔍 Analyze', use_container_width=True):
        if not pipe:
            st.error('❌ Model not loaded. Please refresh the page or train the model.')
        elif text.strip():
            with st.spinner('Analyzing...'):
                # Translate if requested
                if enable_translation and translate_text:
                    with st.status("Translating text...", expanded=True) as status:
                        st.write("Contacting Gemini AI...")
                        translated_text = translate_text(text)
                        if translated_text and translated_text != text:
                            st.write("Translation complete!")
                            with st.expander("View Translated Text"):
                                st.write(translated_text)
                            text = translated_text # Use translated text for analysis
                            status.update(label="Translation Complete", state="complete", expanded=False)
                        else:
                            status.update(label="Translation Failed (using original)", state="error")
                
                cleaned = clean_text(text)
                if cleaned.strip():
                    proba = pipe.predict_proba([cleaned], raw_texts=[text])[0]
                    real_prob = float(proba[0])  # Class 0 is REAL
                    fake_prob = float(proba[1])  # Class 1 is FAKE
                    
                    # Phase 5: OOD Detection
                    ood_val, ood_details = pipe.ood_score(text)
                    
                    # Detect red flags
                    red_flag_score = detect_fake_news_red_flags(text)
                    
                    # Use the configured threshold with red flag adjustment
                    adjusted_real_prob = real_prob * (1 - red_flag_score * 0.3)
                    
                    if adjusted_real_prob >= sensitivity:
                        pred = 'REAL'
                    else:
                        pred = 'FAKE'
                    
                    conf = max(adjusted_real_prob, fake_prob) * 100
                    
                    # Phase 5.3: Calibrate confidence using OOD score
                    if HAS_OOD:
                        conf = calibrate_confidence(conf, ood_val)
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric('Prediction', f"{'🟢 REAL' if pred == 'REAL' else '🔴 FAKE'}")
                    with col2:
                        st.metric('Confidence', f'{conf:.1f}%')
                    with col3:
                        st.metric('Real Score', f'{real_prob:.3f}')
                    with col4:
                        ood_label = f'{ood_val:.2f}'
                        if ood_val > 0.5:
                            st.metric('OOD Score', ood_label, '⚠️ Unusual', delta_color='inverse')
                        else:
                            st.metric('OOD Score', ood_label, '✓ Normal')
                    
                    # Display OOD warning
                    if ood_val > 0.5:
                        st.warning(f'⚠️ **Out-of-Distribution Input** (OOD: {ood_val:.0%}) — This article differs significantly from training data. '
                                   f'ML confidence has been reduced. Gemini AI and Web verification are weighted more heavily.')
                    
                    # Display red flag score
                    if red_flag_score > 0.3:
                        st.error(f'🚩 **RED FLAGS DETECTED:** {red_flag_score*100:.0f}% - This article exhibits fake news characteristics')
                    
                    features = extract_features(text)
                    conspiracy = get_conspiracy_indicators(text)
                    sensationalism = get_sensationalism_score(text)
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric('Sentences', features['sentence_count'])
                    with col2:
                        st.metric('Questions', features['question_count'])
                    with col3:
                        st.metric('Exclamations', features['exclamation_count'])
                    with col4:
                        st.metric('Avg Length', f"{features['avg_sentence_length']:.1f}")
                    
                    if conspiracy > 0:
                        st.warning(f'⚠️ Conspiracy indicators: {conspiracy}')
                    if sensationalism > 0.3:
                        st.warning(f'⚠️ Sensationalism score: {sensationalism:.3f}')
                    
                    st.markdown('---')
                    
                    # Visualizations
                    st.subheader('📊 Content Analysis')
                    viz_col1, viz_col2 = st.columns(2)
                    
                    with viz_col1:
                        # Word Frequency Chart
                        from collections import Counter
                        import plotly.express as px
                        
                        words = [w.lower() for w in cleaned.split() if len(w) > 3]
                        word_counts = Counter(words).most_common(10)
                        
                        if word_counts:
                            df_words = pd.DataFrame(word_counts, columns=['Word', 'Count'])
                            fig_words = px.bar(df_words, x='Count', y='Word', orientation='h', 
                                             title='Top 10 Words', color='Count',
                                             color_continuous_scale='Viridis')
                            fig_words.update_layout(yaxis={'categoryorder':'total ascending'})
                            st.plotly_chart(fig_words, use_container_width=True)
                    
                    with viz_col2:
                        # Sentence Length Distribution (Simple approximation)
                        sentences = [len(s.split()) for s in text.split('.') if s.strip()]
                        if sentences:
                            fig_sent = px.histogram(x=sentences, nbins=10, 
                                                  title='Sentence Length Distribution',
                                                  labels={'x': 'Words per Sentence', 'y': 'Count'},
                                                  color_discrete_sequence=['#636EFA'])
                            st.plotly_chart(fig_sent, use_container_width=True)

                    st.markdown('---')
                    
                    # Explainable AI Section
                    if has_enhanced_features:
                        st.subheader('🧠 Explainable AI - Why This Prediction?')
                        
                        # Individual model predictions
                        with st.expander('🤖 Individual Model Predictions (5-Model Ensemble)', expanded=False):
                            try:
                                model_preds = get_model_predictions(pipe.model, pipe.vectorizer.transform([cleaned]))
                                if model_preds:
                                    cols = st.columns(5)
                                    for i, (model_name, pred_info) in enumerate(model_preds.items()):
                                        with cols[i]:
                                            st.metric(
                                                model_name,
                                                pred_info['prediction'],
                                                f"{pred_info['confidence']:.1f}%"
                                            )
                                else:
                                    st.info('Individual model predictions not available')
                            except:
                                st.info('Model breakdown not available for this model type')
                        
                        # Suspicious phrases highlighting
                        with st.expander('🚩 Suspicious Phrases Detected', expanded=False):
                            suspicious = highlight_suspicious_phrases(text)
                            if suspicious:
                                for finding in suspicious[:10]:  # Show top 10
                                    severity_color = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}
                                    st.markdown(f"{severity_color[finding['severity']]} **{finding['category']}**: \"{finding['text']}\"")
                            else:
                                st.success('✅ No major suspicious phrases detected')
                        
                        # Topic classification
                        topic, topic_conf = classify_topic(text)
                        st.info(f'📂 **Detected Topic:** {topic.title()} (confidence: {topic_conf*100:.0f}%)')
                        
                        # Readability analysis
                        readability = calculate_readability_score(text)
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric('Reading Level', f"Grade {readability['grade_level']}")
                        with col2:
                            st.metric('Difficulty', readability['difficulty'])
                        
                        # Source analysis (if URL detected)
                        domain = extract_domain(text)
                        if domain:
                            source_info = analyze_source(domain)
                            if source_info['category'] == 'trusted':
                                st.success(f'✅ **Source:** {domain} - Trusted News Source ({source_info["reputation"]}% credibility)')
                            elif source_info['category'] == 'unreliable':
                                st.error(f'❌ **Source:** {domain} - Known Unreliable Source ({source_info["reputation"]}% credibility)')
                            else:
                                st.warning(f'⚠️ **Source:** {domain} - Unknown Source ({source_info["reputation"]}% credibility)')
                        
                        st.markdown('---')
                    
                    # Save to database
                    if has_enhanced_features and db:
                        try:
                            article_hash = db.add_analysis(
                                article_text=text,
                                prediction=pred,
                                confidence=conf,
                                real_prob=real_prob,
                                fake_prob=fake_prob,
                                red_flag_score=red_flag_score,
                                source_domain=domain if has_enhanced_features else None,
                                category=topic if has_enhanced_features else None
                            )
                            
                            # User feedback section
                            st.markdown('---')
                            st.subheader('📝 Rate This Analysis')
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                user_rating = st.select_slider(
                                    'Was this prediction accurate?',
                                    options=[1, 2, 3, 4, 5],
                                    value=3,
                                    format_func=lambda x: ['❌ Wrong', '⚠️ Poor', '😐 OK', '👍 Good', '✅ Perfect'][x-1],
                                    key=f"rating_{article_hash}"
                                )
                            with col2:
                                if st.button('Submit Rating', key=f"submit_{article_hash}"):
                                    db.add_feedback(article_hash, user_rating)
                                    st.success('✓ Thanks for your feedback!')
                        except Exception as e:
                            pass  # Silently fail if database unavailable
                    
                    st.markdown('---')
                    
                    # Verdict
                    st.subheader('🎯 AI Verdict')
                    if pred == 'REAL':
                        st.success(f'✅ REAL NEWS - Confidence: {conf:.1f}%')
                    elif pred == 'FAKE':
                        st.error(f'❌ FAKE NEWS - Confidence: {conf:.1f}%')
                    else:
                        st.warning(f'⚠️ UNCERTAIN - Confidence: {conf:.1f}%\nManual verification recommended')
                    
                    # Gemini AI Analysis (Advanced)
                    st.subheader('🤖 Gemini AI Credibility Check (Advanced Analysis)')
                    with st.spinner('🧠 Gemini AI is performing detailed fact-checking...'):
                        gemini_result = gemini_verify_claim(text)
                        if gemini_result:
                            st.success('✅ Gemini AI Analysis Complete')
                            st.info(gemini_result)
                        else:
                            st.warning('⚠️ Could not reach Gemini API')
                    
                    # Web Search for Related Articles (Verification)
                    st.subheader('🌐 Web Verification (Search for Related Articles)')
                    keywords = extract_keywords(text)
                    articles = []
                    if keywords:
                        with st.spinner('🔍 Searching major news sources for related articles...'):
                            articles = search_news_gnews(keywords, max_results=10)
                            
                            if articles:
                                # Professional article summary panel
                                st.success(f'✅ Found {len(articles)} related articles')
                                # build a top-sources table
                                source_rows = []
                                for a in articles:
                                    sname = a.get('source', {}).get('name','Unknown')
                                    title = a.get('title','')[:120]
                                    pub = a.get('publishedAt', 'Unknown')
                                    url = a.get('url','#')
                                    source_rows.append({"Source": sname, "Title": title, "Published": pub, "URL": url})
                                df_sources = pd.DataFrame(source_rows)
                                # Show compact table of sources
                                st.table(df_sources[["Source","Published","Title"]].rename(columns={"Published":"Date","Title":"Headline"}))
                                
                                # Clickable links to articles
                                with st.expander("📰 View Full Articles", expanded=False):
                                    for a in articles[:5]:  # Show top 5
                                        st.markdown(f"**[{a.get('title', 'No title')}]({a.get('url', '#')})**")
                                        st.caption(f"Source: {a.get('source', {}).get('name', 'Unknown')} | Published: {a.get('publishedAt', 'Unknown')}")
                                        if a.get('description'):
                                            st.write(a['description'][:200] + "...")
                                        st.markdown('---')
                            else:
                                st.warning('⚠️ No related articles found. This could indicate:')
                                st.write('- The story is very new or not widely reported')
                                st.write('- The topic is obscure or local')
                                st.write('- The claims may be fabricated')
                    else:
                        st.info('Could not extract meaningful keywords for search')
                    
                    st.markdown('---')
                    
                    # FINAL VERDICT - Combined Analysis
                    st.subheader('⚖️ FINAL VERDICT (Hybrid Analysis)')
                    st.markdown('Combining ML Model + Gemini AI + Web Verification')
                    
                    # Calculate combined score
                    ml_score = real_prob  # ML thinks it's real
                    
                    # Gemini score (parse from result)
                    gemini_score = 0.5  # Default neutral
                    if gemini_result:
                        result_upper = gemini_result.upper()
                        # Check for FALSE/FAKE indicators first (more specific)
                        if 'LIKELY_FALSE' in result_upper or 'LIKELY FALSE' in result_upper:
                            gemini_score = 0.2
                        elif 'FALSE' in result_upper or 'FAKE' in result_upper or 'UNVERIFIABLE' in result_upper:
                            gemini_score = 0.3
                        elif 'CREDIBILITY LEVEL: LOW' in result_upper or 'CREDIBILITY: LOW' in result_upper:
                            gemini_score = 0.2
                        # Check for TRUE/REAL indicators
                        elif 'LIKELY_TRUE' in result_upper or 'LIKELY TRUE' in result_upper:
                            gemini_score = 0.8
                        elif 'TRUE' in result_upper or 'REAL' in result_upper or 'CREDIBLE' in result_upper:
                            gemini_score = 0.7
                        elif 'CREDIBILITY LEVEL: HIGH' in result_upper or 'CREDIBILITY: HIGH' in result_upper:
                            gemini_score = 0.8
                        # Mixed/Medium
                        elif 'MIXED' in result_upper or 'MEDIUM' in result_upper or 'UNCERTAIN' in result_upper:
                            gemini_score = 0.5
                    
                    # Web verification score
                    web_score = 0.5  # Default neutral
                    if articles and len(articles) >= 3:
                        # Found multiple credible sources - likely real
                        web_score = 0.7
                    elif articles and len(articles) >= 1:
                        web_score = 0.6
                    elif keywords and not articles:
                        # Searched but found nothing - suspicious
                        web_score = 0.3
                    
                    # Phase 5.2: Dynamic hybrid weights based on OOD score
                    if HAS_OOD:
                        dw = get_dynamic_weights(ood_val, gemini_available=bool(gemini_result), 
                                                web_results_count=len(articles) if articles else 0)
                        w_ml = dw['ml_weight']
                        w_gemini = dw['gemini_weight']
                        w_web = dw['web_weight']
                    else:
                        w_ml, w_gemini, w_web = 0.50, 0.30, 0.20
                    
                    # Weighted combination with dynamic weights
                    final_score = (ml_score * w_ml) + (gemini_score * w_gemini) + (web_score * w_web)
                    
                    # Red flag adjustment
                    if red_flag_score > 0.3:
                        final_score = final_score * (1 - red_flag_score * 0.5)
                    
                    # Calculate confidence based on final_score
                    # If score is high (>0.65) or low (<0.35), confidence should be high
                    # If score is near 0.5, confidence should be low
                    if final_score >= 0.65:
                        # REAL verdict - confidence based on how high the score is
                        final_confidence = (final_score - 0.5) * 200  # Maps 0.65-1.0 to 30-100%
                    elif final_score <= 0.35:
                        # FAKE verdict - confidence based on how low the score is
                        final_confidence = (0.5 - final_score) * 200  # Maps 0.35-0.0 to 30-100%
                    else:
                        # UNCERTAIN - low confidence (max 30%)
                        final_confidence = abs(final_score - 0.5) * 60  # Maps 0.35-0.65 to 9-0%
                    
                    # Display final verdict
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        ml_verdict = 'REAL' if ml_score > 0.5 else 'FAKE'
                        st.metric('ML Model', ml_verdict, f"{ml_score*100:.0f}% confidence")
                    with col2:
                        gemini_verdict = 'REAL' if gemini_score > 0.5 else 'FAKE'
                        st.metric('Gemini AI', gemini_verdict, f"{gemini_score*100:.0f}% confidence")
                    with col3:
                        web_verdict = 'REAL' if web_score > 0.5 else 'FAKE'
                        web_articles_count = f"{len(articles)} articles" if articles else "No articles"
                        st.metric('Web Verify', web_verdict, web_articles_count)
                    
                    st.markdown('---')
                    
                    # Final decision
                    if final_score >= 0.65:
                        st.success(f'### ✅ FINAL VERDICT: LIKELY REAL')
                        st.success(f'**Confidence: {final_confidence:.1f}%**')
                        st.write('✓ Multiple verification layers indicate this is legitimate news')
                        st.write('✓ ML model, AI analysis, and web sources align')
                    elif final_score <= 0.35:
                        st.error(f'### ❌ FINAL VERDICT: LIKELY FAKE')
                        st.error(f'**Confidence: {final_confidence:.1f}%**')
                        st.write('⚠️ Multiple red flags detected across verification layers')
                        st.write('⚠️ Strong indicators of misinformation or manipulation')
                    else:
                        st.warning(f'### ⚠️ FINAL VERDICT: UNCERTAIN')
                        st.warning(f'**Confidence: {final_confidence:.1f}%**')
                        st.write('• Mixed signals from different verification methods')
                        st.write('• Recommend manual fact-checking before sharing')
                    
                    # Phase 6: Log prediction to monitor
                    if HAS_MONITOR:
                        try:
                            final_verdict_label = 'REAL' if final_score >= 0.65 else 'FAKE' if final_score <= 0.35 else 'UNCERTAIN'
                            _monitor.log_prediction(
                                prediction=pred,
                                confidence=conf,
                                real_prob=real_prob,
                                fake_prob=fake_prob,
                                ood_score=ood_val,
                                ml_weight=w_ml,
                                gemini_weight=w_gemini,
                                web_weight=w_web,
                                red_flag_score=red_flag_score,
                                text_length=len(text),
                                category=topic if has_enhanced_features else None,
                                final_verdict=final_verdict_label,
                                final_score=final_score,
                            )
                        except Exception:
                            pass  # Monitoring should never break analysis
                    
                    # Breakdown
                    with st.expander('📊 See Detailed Breakdown'):
                        st.write(f'**ML Model Score:** {ml_score:.3f} (weight: {w_ml*100:.0f}%)')
                        st.write(f'**Gemini AI Score:** {gemini_score:.3f} (weight: {w_gemini*100:.0f}%)')
                        st.write(f'**Web Verification Score:** {web_score:.3f} (weight: {w_web*100:.0f}%)')
                        st.write(f'**Red Flag Penalty:** {red_flag_score:.3f}')
                        st.write(f'**OOD Score:** {ood_val:.3f}')
                        st.write(f'**Final Combined Score:** {final_score:.3f}')
                        st.write('---')
                        if HAS_OOD and ood_val > 0.3:
                            st.info(f'ℹ️ Dynamic weights active: ML weight reduced from 50% to {w_ml*100:.0f}% due to OOD score of {ood_val:.2f}')
                        st.write('**Scoring:**')
                        st.write('• 0.0-0.35: FAKE NEWS (high confidence)')
                        st.write('• 0.35-0.65: UNCERTAIN (low confidence)')
                        st.write('• 0.65-1.0: REAL NEWS (high confidence)')
                        st.write('---')
                        st.write('**Confidence Calculation:**')
                        if final_score >= 0.65:
                            st.write(f'• REAL verdict: score={final_score:.3f}')
                            st.write(f'• Confidence = (score - 0.5) × 200 = {final_confidence:.1f}%')
                        elif final_score <= 0.35:
                            st.write(f'• FAKE verdict: score={final_score:.3f}')
                            st.write(f'• Confidence = (0.5 - score) × 200 = {final_confidence:.1f}%')
                        else:
                            st.write(f'• UNCERTAIN: score={final_score:.3f} (near 0.5)')
                            st.write(f'• Low confidence = |score - 0.5| × 60 = {final_confidence:.1f}%')
                        st.write('• Low score (near 0.5) = Low confidence (uncertain)')
                        st.write('• High score (near 0 or 1) = High confidence (clear verdict)')
                
                else:
                    st.warning('⚠️ Text is too short or contains no analyzable content after cleaning.')
        else:
            st.warning('⚠️ Please enter some text to analyze.')
