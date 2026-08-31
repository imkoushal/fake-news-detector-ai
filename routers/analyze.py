"""
Analysis & RAG Verification router — ML prediction, smart-verify (RAG), voice transcription, batch analysis, URL fetch.
Extracted from api.py as part of P3-3 router split.
"""
import os
import re
import logging
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict
from scipy.sparse import hstack

from utils import clean_text
from meta_features import extract_single as compute_meta_features
from enhanced_features import detect_fake_news_red_flags
from backend.db import get_db, ph, USE_POSTGRES
from backend.auth import get_user_from_token as _get_user_from_token
from backend import metrics as _metrics
import routers.app_state as _state

logger = logging.getLogger("fake_news_api")

router = APIRouter(tags=["Analysis"])


# ── Pydantic Models ──
class Article(BaseModel):
    text: str
    source: Optional[str] = None
    sensitivity: Optional[float] = None

    @property
    def safe_text(self) -> str:
        return self.text[:50000]


class PredictionResponse(BaseModel):
    prediction: str
    confidence: float
    confidence_tier: str
    real_probability: float
    fake_probability: float
    red_flag_score: float
    input_quality: str = "sufficient"
    fake_indicator_words: List[str] = []
    real_indicator_words: List[str] = []
    category: Optional[str] = None
    timestamp: str
    model_version: str = _state.APP_VERSION


class BatchArticle(BaseModel):
    id: str
    text: str

    @property
    def safe_text(self) -> str:
        return self.text[:50000]


class BatchRequest(BaseModel):
    articles: List[BatchArticle]


class GeminiRequest(BaseModel):
    text: str


class FetchUrlRequest(BaseModel):
    url: str


class TranscribeResponse(BaseModel):
    text: str
    duration_seconds: float | None = None
    language: str | None = None
    model: str = "whisper-large-v3"


class GNewsSearchRequest(BaseModel):
    query: str
    max_results: int = 5


# ── Prompts ──
AI_VERIFY_PROMPT_RAG = """You are an expert fact-checker and media analyst with access to LIVE NEWS from trusted sources.
Analyze the user's news text or claim by cross-referencing it against the provided live news search results.

USER TEXT / CLAIM:
"{text}"

LIVE NEWS EVIDENCE (from GNews API):
{gnews_context}

INSTRUCTIONS:
1. Carefully compare the user's text against the live news evidence.
2. Determine if the claim is LIKELY_TRUE, LIKELY_FALSE, MIXED, or UNVERIFIABLE based on the evidence.
3. Assign a numerical confidence score (0-100%).
4. Provide a structured, objective, line-by-line breakdown explaining:
   - What the user's claim asserts
   - What live news sources report about this topic
   - Key matching or conflicting facts
   - Final reasoning for your verdict
5. Identify top fake-indicator words/phrases and top real-indicator words/phrases in the text.
6. Output your analysis in EXACTLY the following JSON format (no markdown code blocks, just raw valid JSON):

{
  "prediction": "LIKELY_TRUE" | "LIKELY_FALSE" | "MIXED" | "UNVERIFIABLE",
  "confidence": <number 0-100>,
  "verdict_reasoning": "<concise 2-3 sentence summary of the verdict>",
  "detailed_analysis": "<full line-by-line breakdown with evidence citations>",
  "live_sources_used": [
    {"title": "<article title>", "source": "<publisher name>", "url": "<link>"}
  ],
  "fake_indicator_words": ["<word1>", "<word2>"],
  "real_indicator_words": ["<word1>", "<word2>"],
  "category": "Politics" | "Health/Medical" | "Technology" | "Entertainment" | "Finance" | "General News" | "Scam/Fraud"
}
"""

SYSTEM_PROMPT = """You are an expert fact-checker and media analyst.
Analyze news text for accuracy, sensationalism, logical fallacies, and red flags.
Always return response in valid JSON matching the requested schema exactly."""


# ── Word Explainability Helper ──

def _get_top_words(text: str, top_n: int = 5):
    """Extract top real and fake indicator words using TF-IDF feature weights."""
    if not _state.MODEL_LOADED or _state.tfidf is None or _state.model is None:
        return [], []

    try:
        cleaned = clean_text(text)
        tfidf_vec = _state.tfidf.transform([cleaned])
        feature_names = _state.tfidf.get_feature_names_out()

        cx = tfidf_vec.tocoo()
        doc_words = [(feature_names[i], v) for i, v in zip(cx.col, cx.data)]
        if not doc_words:
            return [], []

        if hasattr(_state.model, "feature_importances_"):
            weights = _state.model.feature_importances_[:len(feature_names)]
            word_scores = []
            for word, tfidf_val in doc_words:
                try:
                    idx = list(feature_names).index(word)
                    word_scores.append((word, weights[idx] * tfidf_val))
                except (ValueError, IndexError):
                    continue
            word_scores.sort(key=lambda x: x[1], reverse=True)
            fake_words = [w[0] for w in word_scores[:top_n]]
            real_words = [w[0] for w in word_scores[-top_n:] if w[0] not in fake_words]
            return fake_words, real_words
        elif hasattr(_state.model, "coef_"):
            coefs = _state.model.coef_[0][:len(feature_names)]
            fake_scored = []
            real_scored = []
            for word, tfidf_val in doc_words:
                try:
                    idx = list(feature_names).index(word)
                    score = coefs[idx] * tfidf_val
                    if score < 0:
                        fake_scored.append((word, abs(score)))
                    else:
                        real_scored.append((word, score))
                except (ValueError, IndexError):
                    continue
            fake_scored.sort(key=lambda x: x[1], reverse=True)
            real_scored.sort(key=lambda x: x[1], reverse=True)
            return [w[0] for w in fake_scored[:top_n]], [w[0] for w in real_scored[:top_n]]
    except Exception as e:
        logger.warning(f"Failed to calculate top words: {e}")

    return [], []


# ── Core Smart Verify RAG Logic ──

async def _run_smart_verify(text: str, *, source: str = "web", user_id: int | None = None) -> dict:
    """Core RAG verification logic shared by HTTP endpoint and Telegram bot."""
    from backend.gnews_service import search_gnews_for_claim, format_gnews_for_llm
    from routers.verify import _check_source_credibility

    cleaned_text = text.strip()[:3000]
    if len(cleaned_text) < 10:
        raise HTTPException(400, "Text too short for verification")

    groq_key = os.getenv("GROQ_API_KEY", "")

    # Step 1: Search GNews for live articles
    gnews_results = await search_gnews_for_claim(cleaned_text, max_results=5)
    gnews_context = format_gnews_for_llm(gnews_results)

    # Step 2: Query Groq LLaMA
    if groq_key:
        try:
            from backend.http_client import get_client
            prompt = AI_VERIFY_PROMPT_RAG.format(
                text=cleaned_text,
                gnews_context=gnews_context
            )

            resp = await get_client().post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.2,
                    "max_tokens": 1500,
                    "response_format": {"type": "json_object"}
                },
                timeout=30.0
            )

            if resp.status_code == 200:
                data = resp.json()
                raw_reply = data["choices"][0]["message"]["content"]
                import json as _json
                parsed = _json.loads(raw_reply)

                prediction = str(parsed.get("prediction", "UNVERIFIABLE")).upper()
                confidence = float(parsed.get("confidence", 50.0))
                verdict_reasoning = str(parsed.get("verdict_reasoning", ""))
                detailed_analysis = str(parsed.get("detailed_analysis", ""))
                live_sources = parsed.get("live_sources_used", [])
                fake_words = parsed.get("fake_indicator_words", [])
                real_words = parsed.get("real_indicator_words", [])
                category = parsed.get("category", "General News")

                credibility_info = _check_source_credibility(cleaned_text)

                _metrics.log_event(
                    _metrics.EVENT_CHECK, user_id=user_id, source=source, cost_usd=0.0005,
                    meta={"path": "rag_llm", "prediction": prediction, "has_gnews": bool(gnews_results)},
                )

                response_payload = {
                    "verdict": prediction,
                    "confidence": round(confidence, 1),
                    "verdict_reasoning": verdict_reasoning,
                    "detailed_analysis": detailed_analysis,
                    "live_sources": live_sources,
                    "gnews_articles_found": len(gnews_results),
                    "fake_indicator_words": fake_words,
                    "real_indicator_words": real_words,
                    "category": category,
                    "source_credibility": credibility_info,
                    "method": "RAG_LLM_Verification",
                    "timestamp": datetime.now().isoformat()
                }

                if source == "web":
                    try:
                        from backend.claims_db import save_seo_claim
                        seo_hash = save_seo_claim(
                            claim_text=cleaned_text,
                            verdict=prediction,
                            confidence=confidence,
                            analysis=verdict_reasoning or detailed_analysis[:300],
                            user_id=user_id,
                        )
                        response_payload["claim_hash"] = seo_hash
                    except Exception as _ex:
                        logger.warning(f"Failed to save SEO claim hash: {_ex}")

                return response_payload
            else:
                logger.warning(f"Groq API error {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            logger.error(f"RAG Smart Verify failed: {e}")

    # Fallback to local ML model if Groq unavailable
    if _state.MODEL_LOADED and _state.model is not None and _state.tfidf is not None and _state.scaler is not None:
        def _local_fallback_sync():
            cleaned = clean_text(cleaned_text)
            tfidf_features = _state.tfidf.transform([cleaned])
            text_norm = re.sub(r'\s+', ' ', cleaned_text).strip()
            meta = compute_meta_features(text_norm).reshape(1, -1)
            meta_scaled = _state.scaler.transform(meta)
            features = hstack([tfidf_features, meta_scaled])

            proba = _state.model.predict_proba(features)[0]
            real_prob, fake_prob = float(proba[1]), float(proba[0])

            if real_prob >= 0.7:
                verdict = "LIKELY_TRUE"
            elif fake_prob >= 0.7:
                verdict = "LIKELY_FALSE"
            else:
                verdict = "MIXED"

            conf = max(real_prob, fake_prob) * 100
            fake_words, real_words = _get_top_words(cleaned_text)
            credibility_info = _check_source_credibility(cleaned_text)

            return {
                "verdict": verdict,
                "confidence": round(conf, 1),
                "verdict_reasoning": f"Local ML Ensemble model analysis ({conf:.0f}% confidence).",
                "detailed_analysis": f"Evaluated using local 5-model Voting Ensemble. Real probability: {real_prob:.1%}, Fake probability: {fake_prob:.1%}.",
                "live_sources": [],
                "gnews_articles_found": 0,
                "fake_indicator_words": fake_words,
                "real_indicator_words": real_words,
                "category": "General News",
                "source_credibility": credibility_info,
                "method": "Local_ML_Fallback",
                "timestamp": datetime.now().isoformat()
            }

        return await run_in_threadpool(_local_fallback_sync)

    raise HTTPException(503, "Verification service unavailable. Please set GROQ_API_KEY or ensure ML model is loaded.")


# ── URL Extraction Helper ──

def _extract_article_from_html(html: str) -> dict:
    """Extract article text using BeautifulSoup."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        title = og_title["content"].strip()

    NOISE_TAGS = [
        "script", "style", "nav", "footer", "header", "aside",
        "form", "iframe", "noscript", "svg", "figure", "figcaption",
        "button", "input", "select", "textarea", "label",
    ]
    for tag in NOISE_TAGS:
        for el in soup.find_all(tag):
            el.decompose()

    AD_PATTERNS = re.compile(
        r'(ads?[-_]|advert|banner|sidebar|widget|comment|social|share|'
        r'related|popular|trending|newsletter|subscribe|signup|sign-up|'
        r'cookie|consent|popup|modal|promo|sponsor|recommendation|'
        r'breadcrumb|pagination|menu|toolbar|footer|masthead|'
        r'disclaimer|copyright)',
        re.IGNORECASE
    )
    to_remove = []
    for el in soup.find_all(True):
        if el.attrs is None:
            continue
        el_class = " ".join(el.get("class") or [])
        el_id = el.get("id") or ""
        if AD_PATTERNS.search(el_class) or AD_PATTERNS.search(el_id):
            to_remove.append(el)
    for el in to_remove:
        el.decompose()

    article_container = None
    article_tag = soup.find("article")
    if article_tag:
        article_container = article_tag
    if not article_container:
        main_tag = soup.find("main")
        if main_tag:
            article_container = main_tag
    if not article_container:
        CONTENT_PATTERNS = re.compile(
            r'(article[-_]?body|article[-_]?content|post[-_]?body|post[-_]?content|'
            r'entry[-_]?content|story[-_]?content|'
            r'content[-_]?body|main[-_]?content|page[-_]?content)',
            re.IGNORECASE
        )
        for el in soup.find_all("div"):
            if el.attrs is None:
                continue
            el_class = " ".join(el.get("class") or [])
            el_id = el.get("id") or ""
            if CONTENT_PATTERNS.search(el_class) or CONTENT_PATTERNS.search(el_id):
                article_container = el
                break

    source = article_container if article_container else soup.body or soup
    paragraphs = source.find_all("p")

    BOILERPLATE_KW = [
        "cookie", "subscribe", "sign up", "newsletter",
        "copyright", "all rights reserved", "terms of",
        "privacy policy", "click here", "read more",
        "advertisement", "sponsored", "login", "register",
    ]
    clean_paragraphs = []
    for p in paragraphs:
        text = p.get_text(separator=" ", strip=True)
        if len(text) < 40:
            continue
        lower = text.lower()
        if any(kw in lower for kw in BOILERPLATE_KW):
            continue
        clean_paragraphs.append(text)

    article_text = " ".join(clean_paragraphs[:80])
    return {"text": article_text, "title": title, "word_count": len(article_text.split())}


# ── Endpoints ──

@router.post("/api/v1/analyze", response_model=PredictionResponse)
async def analyze_article(article: Article, request: Request):
    if not _state.MODEL_LOADED or _state.model is None or _state.tfidf is None or _state.scaler is None:
        raise HTTPException(503, "Model not loaded")

    text = article.safe_text.strip()
    word_count = len(text.split())

    if len(text) < 10 or word_count < 3:
        raise HTTPException(400, "Please enter at least a few words to analyze.")

    if word_count < 10:
        input_quality = "short_claim"
    elif word_count < 30:
        input_quality = "headline"
    else:
        input_quality = "sufficient"

    threshold = max(0.0, min(1.0, article.sensitivity if article.sensitivity is not None else _state.MODEL_THRESHOLD))

    def _predict_sync():
        cleaned = clean_text(text)
        tfidf_features = _state.tfidf.transform([cleaned])
        text_normalized = re.sub(r'\s+', ' ', text).strip()
        meta = compute_meta_features(text_normalized).reshape(1, -1)
        meta_scaled = _state.scaler.transform(meta)
        features = hstack([tfidf_features, meta_scaled])

        proba = _state.model.predict_proba(features)[0]
        real_prob, fake_prob = float(proba[1]), float(proba[0])
        red_flag_score = detect_fake_news_red_flags(text)
        prediction = "REAL" if real_prob >= threshold else "FAKE"
        confidence = max(real_prob, fake_prob) * 100

        ood_score = 0.0
        if _state.ood_detector_instance is not None:
            try:
                from ood_detector import calibrate_confidence
                ood_score, _ood_details = _state.ood_detector_instance.score(cleaned)
                confidence = calibrate_confidence(confidence, ood_score)
            except Exception as e:
                logger.warning(f"OOD scoring failed (using raw confidence): {e}")

        fake_words, real_words = _get_top_words(text)

        return {
            "prediction": prediction, "confidence": confidence,
            "real_prob": real_prob, "fake_prob": fake_prob,
            "red_flag_score": red_flag_score,
            "fake_words": fake_words, "real_words": real_words,
        }

    result = await run_in_threadpool(_predict_sync)
    prediction = result["prediction"]
    confidence = result["confidence"]
    real_prob = result["real_prob"]
    fake_prob = result["fake_prob"]
    red_flag_score = result["red_flag_score"]
    fake_words = result["fake_words"]
    real_words = result["real_words"]

    if input_quality == "short_claim":
        confidence = min(confidence, 60.0)
    elif input_quality == "headline":
        confidence = min(confidence, 80.0)

    if 0.45 <= real_prob <= 0.60:
        prediction = "UNCERTAIN"
        confidence_tier = "Insufficient Signal"
    elif confidence >= 90:
        confidence_tier = "Verified Real" if prediction == "REAL" else "Confirmed Fake"
    elif confidence >= 75:
        confidence_tier = "Likely Real" if prediction == "REAL" else "Likely Fake"
    elif confidence >= 60:
        confidence_tier = "Slightly Real" if prediction == "REAL" else "Slightly Fake"
    elif confidence >= 50:
        confidence_tier = "Borderline Real" if prediction == "REAL" else "Borderline Fake"
    else:
        confidence_tier = "Borderline Real" if prediction == "REAL" else "Borderline Fake"

    user_id = await run_in_threadpool(_get_user_from_token, request)
    _metrics.log_event(
        _metrics.EVENT_CHECK, user_id=user_id, source="web", cost_usd=0.0,
        meta={"path": "ml", "prediction": prediction, "quality": input_quality},
    )

    def _save_analysis_sync():
        if user_id and input_quality == "sufficient":
            conn = get_db()
            c = conn.cursor()
            try:
                preview = text[:150] + ("..." if len(text) > 150 else "")
                c.execute(
                    f"INSERT INTO analyses (user_id, text_preview, prediction, confidence, real_prob, fake_prob, red_flag_score) VALUES ({ph(7)})",
                    (user_id, preview, prediction, round(confidence, 1), round(real_prob, 3), round(fake_prob, 3), round(red_flag_score, 3))
                )
                conn.commit()
            except Exception as e:
                logger.error(f"Failed to save analysis history: {e}")
                conn.rollback()
            finally:
                conn.close()

    await run_in_threadpool(_save_analysis_sync)

    return PredictionResponse(
        prediction=prediction,
        confidence=round(confidence, 1),
        confidence_tier=confidence_tier,
        real_probability=round(real_prob, 3),
        fake_probability=round(fake_prob, 3),
        red_flag_score=round(red_flag_score * 100),
        input_quality=input_quality,
        fake_indicator_words=fake_words,
        real_indicator_words=real_words,
        timestamp=datetime.now().isoformat()
    )


@router.post("/api/v1/smart-verify")
async def smart_verify(req: GeminiRequest, request: Request):
    """Verify a claim in real-time using GNews API + Groq LLaMA 3.3 70B."""
    user_id = _get_user_from_token(request)
    cached = _state.claim_cache.get(req.text, "smart-verify")
    if cached:
        cached["cache_status"] = "hit"
        return cached

    result = await _run_smart_verify(req.text, source="web", user_id=user_id)
    result["cache_status"] = "miss"
    _state.claim_cache.set(req.text, "smart-verify", result)
    return result


@router.post("/api/v1/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(request: Request, file: UploadFile = File(...)):
    """Transcribe uploaded audio file using Groq Whisper API."""
    user_id = _get_user_from_token(request)
    groq_key = os.getenv("GROQ_API_KEY", "")
    if not groq_key:
        raise HTTPException(503, "Groq API key is not configured for transcription")

    content = await file.read()
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(400, "Audio file exceeds 25MB limit")

    filename = file.filename or "audio.wav"

    try:
        from backend.http_client import get_client
        resp = await get_client().post(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {groq_key}"},
            files={"file": (filename, content, file.content_type or "audio/wav")},
            data={"model": "whisper-large-v3", "response_format": "verbose_json"},
            timeout=60.0
        )

        if resp.status_code != 200:
            logger.error(f"Groq Whisper API returned status {resp.status_code}: {resp.text}")
            raise HTTPException(502, "Audio transcription failed at provider")

        data = resp.json()
        transcript_text = data.get("text", "").strip()
        duration = data.get("duration", None)
        language = data.get("language", None)

        if not transcript_text:
            raise HTTPException(422, "No speech detected in audio file")

        _metrics.log_event(_metrics.EVENT_CHECK, user_id=user_id, source="web", meta={"path": "transcribe"})

        return TranscribeResponse(
            text=transcript_text,
            duration_seconds=round(duration, 2) if duration else None,
            language=language,
            model="whisper-large-v3"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(500, f"Transcription error: {str(e)}")


@router.post("/api/v1/gemini-verify")
async def gemini_verify(req: GeminiRequest, request: Request):
    """Alias for /smart-verify (backward compatibility)."""
    return await smart_verify(req, request)


@router.post("/api/v1/gnews-search")
async def gnews_search_endpoint(req: GNewsSearchRequest, request: Request):
    """Direct GNews API search for live news corroboration."""
    from backend.gnews_service import search_gnews_for_claim

    articles = await search_gnews_for_claim(req.query, max_results=min(req.max_results, 10))
    return {
        "query": req.query,
        "total_results": len(articles),
        "articles": articles,
        "timestamp": datetime.now().isoformat()
    }


@router.post("/api/v1/batch")
async def batch_analyze(batch: BatchRequest, request: Request):
    """Analyze up to 50 articles in a single request."""
    if not _state.MODEL_LOADED or _state.model is None or _state.tfidf is None or _state.scaler is None:
        raise HTTPException(503, "Model not loaded")

    if len(batch.articles) > 50:
        raise HTTPException(400, "Batch limit exceeded (max 50 articles per request)")
    if len(batch.articles) == 0:
        raise HTTPException(400, "Empty batch request")

    def _predict_batch_sync():
        results = []
        for article in batch.articles:
            text = article.safe_text.strip()
            if len(text) < 10:
                results.append({
                    "id": article.id, "error": "Text too short",
                    "prediction": "UNVERIFIABLE", "confidence": 0.0
                })
                continue

            cleaned = clean_text(text)
            tfidf_features = _state.tfidf.transform([cleaned])
            text_norm = re.sub(r'\s+', ' ', text).strip()
            meta = compute_meta_features(text_norm).reshape(1, -1)
            meta_scaled = _state.scaler.transform(meta)
            features = hstack([tfidf_features, meta_scaled])

            proba = _state.model.predict_proba(features)[0]
            real_prob, fake_prob = float(proba[1]), float(proba[0])

            if 0.45 <= real_prob <= 0.60:
                prediction = "UNCERTAIN"
            else:
                prediction = "REAL" if real_prob >= _state.MODEL_THRESHOLD else "FAKE"

            confidence = max(real_prob, fake_prob) * 100
            red_flag_score = detect_fake_news_red_flags(text)

            results.append({
                "id": article.id, "prediction": prediction,
                "confidence": round(confidence, 1),
                "real_probability": round(real_prob, 3),
                "fake_probability": round(fake_prob, 3),
                "red_flag_score": round(red_flag_score * 100),
            })
        return results

    results = await run_in_threadpool(_predict_batch_sync)
    return {
        "total": len(batch.articles),
        "processed": len(results),
        "results": results,
        "timestamp": datetime.now().isoformat()
    }


@router.post("/api/v1/fetch-url")
async def fetch_url(req: FetchUrlRequest, request: Request):
    """Fetch and extract article text from a URL using 3-tier extraction."""
    url = req.url.strip()
    if not url.startswith(("http://", "https://")):
        raise HTTPException(400, "Invalid URL — must start with http:// or https://")

    try:
        from backend.ssrf import validate_url
        validate_url(url)
    except ValueError as e:
        logger.warning(f"SSRF blocked: {url} — {e}")
        raise HTTPException(403, "This URL is not allowed for security reasons")

    # Tier 1: newspaper4k
    try:
        from backend.ssrf import safe_get
        from backend.http_client import get_client
        from newspaper import Article as NewspaperArticle

        resp = await safe_get(get_client(), url)
        if resp.status_code == 200 and len(resp.text) > 200:
            article = NewspaperArticle(url=url)
            article.set_html(resp.text)
            article.parse()
            text = article.text.strip()
            if len(text.split()) >= 20:
                logger.info(f"URL extraction via newspaper4k: {len(text.split())} words from {url}")
                return {
                    "url": url, "title": article.title or "",
                    "text": text, "word_count": len(text.split()),
                    "authors": article.authors,
                    "publish_date": str(article.publish_date) if article.publish_date else None,
                    "top_image": article.top_image or "",
                    "extraction_method": "newspaper4k"
                }
    except Exception as e:
        logger.warning(f"Tier 1 (newspaper4k) failed for {url}: {e}")

    # Tier 2: BeautifulSoup
    try:
        from backend.ssrf import safe_get
        from backend.http_client import get_client
        resp = await safe_get(get_client(), url)
        if resp.status_code == 200:
            result = _extract_article_from_html(resp.text)
            if result["word_count"] >= 20:
                logger.info(f"URL extraction via BS4: {result['word_count']} words from {url}")
                return {**result, "url": url, "extraction_method": "beautifulsoup"}
    except Exception as e:
        logger.warning(f"Tier 2 (BS4) failed for {url}: {e}")

    raise HTTPException(422, "Could not extract enough text from this URL. Try pasting the article text directly.")
