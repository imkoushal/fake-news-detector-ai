"""
Verification, Fact-Checking, Safe Browsing, Credibility & API Keys router.
Extracted from api.py as part of P3-3 router split.
"""
import os
import re
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.auth import get_user_from_token as _get_user_from_token
from backend.credibility_db import SOURCE_CREDIBILITY_DB
from backend.threat_patterns import scan_india_threats as _scan_india_threats
import routers.app_state as _state

logger = logging.getLogger("fake_news_api")

router = APIRouter(tags=["Verification"])

GOOGLE_FACTCHECK_API_KEY = os.getenv("GOOGLE_FACTCHECK_API_KEY", "")
GOOGLE_SAFE_BROWSING_API_KEY = os.getenv("GOOGLE_SAFE_BROWSING_API_KEY", "")


# ── Pydantic Models ──
class VerificationRequest(BaseModel):
    text: str


# ── API Key Validation Helpers ──

def validate_api_key_header(request: Request) -> dict | None:
    """Check X-API-Key header. Returns key info or None."""
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return None

    from backend.api_keys import validate_api_key
    return validate_api_key(api_key)


def check_api_key_or_session(request: Request) -> int | None:
    """Allow access via session auth OR API key. Returns user_id or None."""
    user_id = _get_user_from_token(request)
    if user_id:
        return user_id

    key_info = validate_api_key_header(request)
    if key_info is None:
        return None

    if not key_info["allowed"]:
        raise HTTPException(
            429,
            f"API key daily limit reached ({key_info['daily_limit']} requests/day). "
            f"Upgrade your plan or wait until tomorrow.",
        )

    from backend.api_keys import record_usage
    record_usage(key_info["key_id"])

    return key_info["user_id"]


# ── Helper Functions ──

async def _run_factcheck_search(text: str):
    """Search Google Fact Check API for existing fact-checks matching this claim."""
    if not GOOGLE_FACTCHECK_API_KEY or len(text.strip()) < 10:
        return None

    try:
        from utils import extract_keywords
        keywords = extract_keywords(text, max_keywords=5)
        if not keywords:
            keywords = " ".join(text.split()[:8])

        from backend.http_client import get_client
        params = {
            "query": keywords,
            "key": GOOGLE_FACTCHECK_API_KEY,
            "languageCode": "en",
        }
        resp = await get_client().get(
            "https://factchecktools.googleapis.com/v1alpha1/claims:search",
            params=params
        )
        if resp.status_code != 200:
            logger.warning(f"Fact Check API returned status {resp.status_code}")
            return None

        data = resp.json()
        claims = data.get("claims", [])

        if not claims:
            return {
                "found": False,
                "total_claims": 0,
                "reviews": [],
                "factcheck_score": 0.5,
            }

        reviews = []
        verdict_scores = []
        for claim in claims[:5]:
            claim_text = claim.get("text", "")
            claimant = claim.get("claimant", "Unknown")
            for review in claim.get("claimReview", []):
                publisher = review.get("publisher", {}).get("name", "Unknown")
                url = review.get("url", "")
                title = review.get("title", "")
                rating = review.get("textualRating", "").lower()
                review_date = review.get("reviewDate", "")[:10]

                false_indicators = ["false", "fake", "pants on fire", "misleading",
                                    "mostly false", "incorrect", "wrong", "hoax",
                                    "fabricated", "scam", "satire", "no evidence",
                                    "unproven", "not true", "manipulated"]
                true_indicators = ["true", "correct", "accurate", "mostly true",
                                   "verified", "confirmed", "real", "factual"]
                mixed_indicators = ["half true", "mixture", "partly", "partially",
                                    "needs context", "missing context", "exaggerated"]

                if any(ind in rating for ind in false_indicators):
                    score = 0.15
                elif any(ind in rating for ind in true_indicators):
                    score = 0.9
                elif any(ind in rating for ind in mixed_indicators):
                    score = 0.5
                else:
                    score = 0.5

                verdict_scores.append(score)
                reviews.append({
                    "claim": claim_text[:200],
                    "claimant": claimant,
                    "publisher": publisher,
                    "rating": review.get("textualRating", "Unknown"),
                    "url": url,
                    "title": title[:150],
                    "date": review_date,
                    "score": score,
                })

        avg_score = sum(verdict_scores) / len(verdict_scores) if verdict_scores else 0.5

        return {
            "found": True,
            "total_claims": len(claims),
            "reviews": reviews[:5],
            "factcheck_score": round(avg_score, 2),
        }

    except Exception as e:
        logger.error(f"Fact Check API search failed: {e}")
        return None


def _extract_urls_from_text(text: str):
    """Extract all URLs from article text."""
    url_pattern = r'https?://(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}(?:/[^\s<>"{}|\\^`\[\]]*)?'
    urls = re.findall(url_pattern, text)
    seen = set()
    unique = []
    for u in urls:
        u_clean = u.rstrip('.,;:!?)\'\"')
        if u_clean not in seen:
            seen.add(u_clean)
            unique.append(u_clean)
    return unique[:20]


async def _check_safe_browsing(urls: list):
    """Check URLs against Google Safe Browsing API."""
    if not GOOGLE_SAFE_BROWSING_API_KEY or not urls:
        return None

    try:
        from backend.http_client import get_client
        payload = {
            "client": {
                "clientId": "fake-news-detector",
                "clientVersion": _state.APP_VERSION
            },
            "threatInfo": {
                "threatTypes": [
                    "MALWARE",
                    "SOCIAL_ENGINEERING",
                    "UNWANTED_SOFTWARE",
                    "POTENTIALLY_HARMFUL_APPLICATION"
                ],
                "platformTypes": ["ANY_PLATFORM"],
                "threatEntryTypes": ["URL"],
                "threatEntries": [{"url": u} for u in urls]
            }
        }

        resp = await get_client().post(
            f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={GOOGLE_SAFE_BROWSING_API_KEY}",
            json=payload
        )

        if resp.status_code != 200:
            logger.warning(f"Safe Browsing API returned status {resp.status_code}")
            return None

        data = resp.json()
        matches = data.get("matches", [])

        threats = []
        threat_types_found = set()
        for match in matches:
            url = match.get("threat", {}).get("url", "")
            threat_type = match.get("threatType", "UNKNOWN")
            platform = match.get("platformType", "UNKNOWN")
            threat_types_found.add(threat_type)

            threat_labels = {
                "MALWARE": "Malware Distribution",
                "SOCIAL_ENGINEERING": "Phishing / Social Engineering",
                "UNWANTED_SOFTWARE": "Unwanted Software",
                "POTENTIALLY_HARMFUL_APPLICATION": "Harmful Application"
            }

            threats.append({
                "url": url,
                "threat_type": threat_type,
                "threat_label": threat_labels.get(threat_type, threat_type),
                "platform": platform,
            })

        if not urls:
            safety_score = 1.0
        else:
            flagged_count = len(set(t["url"] for t in threats))
            safety_score = 1.0 - (flagged_count / len(urls))

        return {
            "urls_checked": len(urls),
            "urls_flagged": len(threats),
            "threats": threats,
            "threat_types": list(threat_types_found),
            "safety_score": round(safety_score, 2),
            "all_safe": len(threats) == 0,
        }

    except Exception as e:
        logger.error(f"Safe Browsing API check failed: {e}")
        return None


def _check_source_credibility(text: str) -> dict:
    """Extract domains from text and check their credibility scores."""
    urls = _extract_urls_from_text(text)
    if not urls:
        return {"sources_found": 0, "sources": [], "avg_credibility": None}

    sources = []
    seen_domains = set()

    for url in urls:
        try:
            from urllib.parse import urlparse as _urlparse
            parsed = _urlparse(url)
            domain = parsed.netloc.replace("www.", "").lower()
        except Exception:
            continue

        if not domain or domain in seen_domains:
            continue
        seen_domains.add(domain)

        entry = SOURCE_CREDIBILITY_DB.get(domain)
        if not entry:
            for known_domain, data in SOURCE_CREDIBILITY_DB.items():
                if domain.endswith(known_domain) or known_domain in domain:
                    entry = data
                    break

        if entry:
            score, category, bias, desc = entry
            tier = "gold" if score >= 93 else "trusted" if score >= 80 else "mixed" if score >= 50 else "unreliable"
            sources.append({
                "domain": domain,
                "url": url,
                "credibility_score": score,
                "category": category,
                "bias": bias,
                "description": desc,
                "tier": tier,
                "known": True,
            })
        else:
            sources.append({
                "domain": domain,
                "url": url,
                "credibility_score": 50,
                "category": "unknown",
                "bias": "unknown",
                "description": "Domain not in credibility database",
                "tier": "unknown",
                "known": False,
            })

    known_sources = [s for s in sources if s["known"]]
    avg_cred = round(sum(s["credibility_score"] for s in known_sources) / len(known_sources), 1) if known_sources else None

    return {
        "sources_found": len(sources),
        "known_sources": len(known_sources),
        "unknown_sources": len(sources) - len(known_sources),
        "avg_credibility": avg_cred,
        "sources": sources,
        "database_size": len(SOURCE_CREDIBILITY_DB),
    }


# ── Endpoints ──

@router.post("/api/v1/fact-check")
async def fact_check_search(req: VerificationRequest, request: Request):
    """Search Google's Fact Check database for existing fact-checks on a claim."""
    text = req.text.strip()[:3000]
    if len(text) < 10:
        raise HTTPException(400, "Text too short for fact-check search")

    cached = _state.claim_cache.get(text, "fact-check")
    if cached:
        cached["cache_status"] = "hit"
        return cached

    result = await _run_factcheck_search(text)

    if result is None:
        if not GOOGLE_FACTCHECK_API_KEY:
            return {
                "available": False,
                "found": False,
                "total_claims": 0,
                "reviews": [],
                "factcheck_score": 0.5,
                "message": "Fact Check API not configured. Set GOOGLE_FACTCHECK_API_KEY env var."
            }
        return {
            "available": False,
            "found": False,
            "total_claims": 0,
            "reviews": [],
            "factcheck_score": 0.5,
            "message": "Fact Check search failed"
        }

    result_response = {**result, "available": True, "cache_status": "miss"}
    _state.claim_cache.set(text, "fact-check", result_response)
    return result_response


@router.post("/api/v1/safe-browsing")
async def safe_browsing_check(req: VerificationRequest, request: Request):
    """Check URLs in article text against Google Safe Browsing database."""
    text = req.text.strip()[:5000]
    if len(text) < 10:
        raise HTTPException(400, "Text too short")

    urls = _extract_urls_from_text(text)

    if urls:
        cached = _state.claim_cache.get(text, "safe-browsing")
        if cached:
            cached["cache_status"] = "hit"
            return cached

    if not urls:
        return {
            "available": True,
            "urls_checked": 0,
            "urls_flagged": 0,
            "threats": [],
            "threat_types": [],
            "safety_score": 1.0,
            "all_safe": True,
            "message": "No URLs found in text"
        }

    if not GOOGLE_SAFE_BROWSING_API_KEY:
        return {
            "available": False,
            "urls_checked": len(urls),
            "urls_flagged": 0,
            "threats": [],
            "threat_types": [],
            "safety_score": 1.0,
            "all_safe": True,
            "message": "Safe Browsing API not configured. Set GOOGLE_SAFE_BROWSING_API_KEY env var."
        }

    result = await _check_safe_browsing(urls)

    if result is None:
        return {
            "available": False,
            "urls_checked": len(urls),
            "urls_flagged": 0,
            "threats": [],
            "threat_types": [],
            "safety_score": 1.0,
            "all_safe": True,
            "message": "Safe Browsing check failed"
        }

    sb_response = {**result, "available": True, "urls_found": urls, "cache_status": "miss"}
    _state.claim_cache.set(text, "safe-browsing", sb_response)
    return sb_response


@router.get("/api/v1/cache-stats")
async def cache_stats():
    """Return claim cache hit/miss statistics for monitoring."""
    return _state.claim_cache.stats()


@router.post("/api/v1/source-credibility")
async def check_source_credibility(req: VerificationRequest, request: Request):
    """Check credibility of news sources/domains found in article text."""
    text = req.text.strip()[:5000]
    if len(text) < 10:
        raise HTTPException(400, "Text too short")

    cached = _state.claim_cache.get(text, "source-credibility")
    if cached:
        cached["cache_status"] = "hit"
        return cached

    result = _check_source_credibility(text)
    result["available"] = True
    result["cache_status"] = "miss"
    _state.claim_cache.set(text, "source-credibility", result)
    return result


@router.post("/api/v1/india-threat-scan")
async def india_threat_scan(req: VerificationRequest, request: Request):
    """Scan article text for India-specific misinformation and scam patterns."""
    text = req.text.strip()[:5000]
    if len(text) < 10:
        raise HTTPException(400, "Text too short")

    cached = _state.claim_cache.get(text, "india-threat")
    if cached:
        cached["cache_status"] = "hit"
        return cached

    result = _scan_india_threats(text)
    result["available"] = True
    result["cache_status"] = "miss"
    _state.claim_cache.set(text, "india-threat", result)
    return result


# ── Public API Key Management ──

@router.post("/api/v1/api-keys", tags=["API Keys"])
async def create_api_key(request: Request, body: dict | None = None):
    """Create a new API key for the authenticated user."""
    from backend.api_keys import generate_api_key, list_user_keys

    user_id = _get_user_from_token(request)
    if not user_id:
        raise HTTPException(401, "Authentication required")

    existing = list_user_keys(user_id)
    if len(existing) >= 5:
        raise HTTPException(400, "Maximum of 5 API keys per account")

    name = (body or {}).get("name", "Default")
    if len(name) > 50:
        name = name[:50]

    result = generate_api_key(user_id, name)
    return {
        "message": "API key created. Save it now — it won't be shown again!",
        **result,
    }


@router.get("/api/v1/api-keys", tags=["API Keys"])
async def list_api_keys(request: Request):
    """List all API keys for the authenticated user."""
    from backend.api_keys import list_user_keys

    user_id = _get_user_from_token(request)
    if not user_id:
        raise HTTPException(401, "Authentication required")

    keys = list_user_keys(user_id)
    return {"keys": keys, "count": len(keys)}


@router.delete("/api/v1/api-keys/{key_id}", tags=["API Keys"])
async def revoke_api_key_endpoint(key_id: int, request: Request):
    """Revoke (deactivate) an API key."""
    from backend.api_keys import revoke_api_key

    user_id = _get_user_from_token(request)
    if not user_id:
        raise HTTPException(401, "Authentication required")

    success = revoke_api_key(user_id, key_id)
    if not success:
        raise HTTPException(404, "API key not found")
    return {"message": "API key revoked", "key_id": key_id}


@router.get("/api/v1/api-keys/{key_id}/usage", tags=["API Keys"])
async def get_api_key_usage(key_id: int, request: Request, days: int = 7):
    """Get usage history for a specific API key."""
    from backend.api_keys import get_key_usage, list_user_keys

    user_id = _get_user_from_token(request)
    if not user_id:
        raise HTTPException(401, "Authentication required")

    user_keys = list_user_keys(user_id)
    if not any(k["id"] == key_id for k in user_keys):
        raise HTTPException(404, "API key not found")

    usage = get_key_usage(key_id, min(days, 90))
    return {"key_id": key_id, "days": days, "usage": usage}
