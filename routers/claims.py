"""
SEO & Claims router — public claim rendering, SVG card generation, JSON-LD, sitemap, robots.txt.
Extracted from api.py as part of P3-3 router split.
"""
import logging
import html as html_mod
import json as json_mod
from functools import lru_cache

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response

from backend.claims_db import get_seo_claim, list_all_claim_hashes
from backend.card_generator import generate_verdict_card
import routers.app_state as _state

logger = logging.getLogger("fake_news_api")

router = APIRouter(tags=["SEO"])

VALID_VERDICTS = ("LIKELY_TRUE", "LIKELY_FALSE", "MIXED", "UNVERIFIABLE")

# Claim pages need no JS, no fetches and no framing, so they can carry a far
# stricter policy than the app-wide one in add_security_headers (which must
# stay permissive enough for the SPA's inline bootstrap, Google Sign-In and
# Google Fonts).
_CLAIM_PAGE_CSP = {
    "Content-Security-Policy": (
        "default-src 'none'; img-src https: data:; style-src 'unsafe-inline'; "
        "base-uri 'none'; frame-ancestors 'none'; form-action 'none'"
    )
}


def _safe_verdict(raw) -> str:
    """Clamp a stored verdict to the known set."""
    v = str(raw or "").strip().upper()
    return v if v in VALID_VERDICTS else "UNVERIFIABLE"


def _safe_confidence(raw) -> float:
    """Coerce a stored confidence to a formattable float."""
    try:
        return max(0.0, min(100.0, float(raw or 0)))
    except (TypeError, ValueError):
        return 0.0


def _json_ld(payload: dict) -> str:
    """Serialise a dict for embedding inside <script type="application/ld+json">."""
    return (
        json_mod.dumps(payload, ensure_ascii=False)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


@lru_cache(maxsize=1)
def _spa_index_html() -> str | None:
    """Read the built SPA shell once, or None if the frontend isn't built."""
    try:
        index = _state.BASE_DIR / "landing-page" / "dist" / "index.html"
        return index.read_text(encoding="utf-8")
    except OSError:
        return None


def _build_spa_redirect(claim_hash: str, *, title: str = "VerifAI Fact Checker",
                        description: str = "AI-powered fact checking",
                        card_url: str = "", page_url: str = "") -> str:
    """Build the HTML page that loads the React SPA for a claim page."""
    base_url = "https://fake-news-detector-8djq.onrender.com"
    if not page_url:
        page_url = f"{base_url}/claim/{claim_hash}"
    if not card_url:
        card_url = f"{base_url}/api/v1/claim/{claim_hash}/card.svg"

    og_tags = f"""
<title>{title}</title>
<meta name="description" content="{description}"/>
<meta property="og:title" content="{title}"/>
<meta property="og:description" content="{description}"/>
<meta property="og:image" content="{card_url}"/>
<meta property="og:image:width" content="1200"/>
<meta property="og:image:height" content="630"/>
<meta property="og:url" content="{page_url}"/>
<meta property="og:type" content="article"/>
<meta property="og:site_name" content="VerifAI Fact Checker"/>
<meta name="twitter:card" content="summary_large_image"/>
<meta name="twitter:title" content="{title}"/>
<meta name="twitter:description" content="{description}"/>
<meta name="twitter:image" content="{card_url}"/>"""

    shell = _spa_index_html()
    if shell and "<head>" in shell:
        return shell.replace("<head>", f"<head>{og_tags}", 1)

    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>{og_tags}
</head><body>
<h1>{title}</h1><p>{description}</p>
<p><a href="{page_url}">View full report on VerifAI</a></p>
</body></html>"""


# ── Claim Endpoints ──

@router.get("/api/v1/claim/{claim_hash}")
def get_seo_claim_endpoint(claim_hash: str):
    """Fetch a verified claim by its unique hash for public SEO pages."""
    try:
        claim = get_seo_claim(claim_hash)
        if not claim:
            raise HTTPException(404, "Claim not found")
        return claim
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching claim: {e}")
        raise HTTPException(500, "Internal server error")


@router.get("/api/v1/claim/{claim_hash}/card.svg")
def get_claim_card_svg(claim_hash: str):
    """Generate a shareable SVG verdict card for social media previews."""
    claim = get_seo_claim(claim_hash)
    if not claim:
        raise HTTPException(404, "Claim not found")

    svg = generate_verdict_card(
        claim_text=claim.get("claim_text", claim.get("text", "Claim text unavailable")),
        verdict=_safe_verdict(claim.get("verdict")),
        confidence=_safe_confidence(claim.get("confidence")),
        analysis=claim.get("analysis", ""),
    )
    return Response(content=svg, media_type="image/svg+xml",
                    headers={"Cache-Control": "public, max-age=86400",
                             **_CLAIM_PAGE_CSP})


@router.get("/claim/{claim_hash}")
def claim_og_page(claim_hash: str, request: Request):
    """Server-rendered HTML with OG meta tags for social crawlers."""
    ua = (request.headers.get("user-agent") or "").lower()
    is_crawler = any(bot in ua for bot in [
        "whatsapp", "telegrambot", "twitterbot", "facebookexternalhit",
        "linkedinbot", "slackbot", "googlebot", "bingbot", "discordbot",
    ])

    claim = get_seo_claim(claim_hash)
    if not claim and not is_crawler:
        return HTMLResponse(status_code=200, content=_build_spa_redirect(claim_hash))

    if not claim:
        raise HTTPException(404, "Claim not found")

    verdict_key = _safe_verdict(claim.get("verdict"))
    verdict = verdict_key.replace("_", " ")
    confidence = _safe_confidence(claim.get("confidence"))
    text = claim.get("claim_text", claim.get("text", ""))[:200]
    analysis = claim.get("analysis", "")[:300]
    safe_text = html_mod.escape(text)
    safe_analysis = html_mod.escape(analysis)
    base_url = "https://fake-news-detector-8djq.onrender.com"
    card_url = f"{base_url}/api/v1/claim/{claim_hash}/card.svg"
    page_url = f"{base_url}/claim/{claim_hash}"

    title = html_mod.escape(
        f"VerifAI: {verdict} ({confidence:.0f}% confidence)", quote=True
    )
    description = safe_analysis if safe_analysis else f'Claim: "{safe_text[:120]}..."'

    if is_crawler:
        verdict_name_map = {"LIKELY_TRUE": "True", "LIKELY_FALSE": "False", "MIXED": "Mixture", "UNVERIFIABLE": "Unverifiable"}
        rating_val_map = {"LIKELY_TRUE": 4, "LIKELY_FALSE": 1, "MIXED": 3, "UNVERIFIABLE": 3}
        jsonld = _json_ld({
            "@context": "https://schema.org",
            "@type": "ClaimReview",
            "url": page_url,
            "claimReviewed": text[:500],
            "author": {"@type": "Organization", "name": "VerifAI", "url": base_url},
            "reviewRating": {
                "@type": "Rating",
                "ratingValue": rating_val_map.get(verdict_key, 3),
                "bestRating": 5, "worstRating": 1,
                "alternateName": verdict_name_map.get(verdict_key, "Unverifiable"),
            },
            "itemReviewed": {"@type": "Claim", "name": text[:200]},
        })

        og_html = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"/>
<title>{title}</title>
<meta name="description" content="{description}"/>
<link rel="canonical" href="{page_url}"/>
<meta property="og:title" content="{title}"/>
<meta property="og:description" content="{description}"/>
<meta property="og:image" content="{card_url}"/>
<meta property="og:image:width" content="1200"/>
<meta property="og:image:height" content="630"/>
<meta property="og:url" content="{page_url}"/>
<meta property="og:type" content="article"/>
<meta property="og:site_name" content="VerifAI Fact Checker"/>
<meta name="twitter:card" content="summary_large_image"/>
<meta name="twitter:title" content="{title}"/>
<meta name="twitter:description" content="{description}"/>
<meta name="twitter:image" content="{card_url}"/>
<script type="application/ld+json">{jsonld}</script>
</head><body><h1>{title}</h1><p>{description}</p>
<p><a href="{page_url}">View full report on VerifAI</a></p>
</body></html>"""
        return HTMLResponse(content=og_html, headers=_CLAIM_PAGE_CSP)

    return HTMLResponse(content=_build_spa_redirect(claim_hash, title=title,
                        description=description, card_url=card_url, page_url=page_url))


@router.get("/sitemap.xml")
def sitemap_xml():
    """Dynamic XML sitemap listing all verified claim pages."""
    base = "https://fake-news-detector-8djq.onrender.com"
    claims = list_all_claim_hashes()

    urls = [f"""  <url>
<loc>{base}/claim/{c['hash']}</loc>
<lastmod>{c['created_at'][:10] if c.get('created_at') else '2026-01-01'}</lastmod>
<changefreq>monthly</changefreq>
<priority>0.7</priority>
  </url>""" for c in claims]

    static_pages = [
        ("", "daily", "1.0"),
        ("/about", "monthly", "0.5"),
        ("/privacy", "yearly", "0.3"),
    ]
    for path, freq, prio in static_pages:
        urls.insert(0, f"""  <url>
<loc>{base}{path}</loc>
<changefreq>{freq}</changefreq>
<priority>{prio}</priority>
  </url>""")

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>"""
    return Response(content=xml, media_type="application/xml",
                    headers={"Cache-Control": "public, max-age=3600"})


@router.get("/robots.txt")
def robots_txt():
    """Serve robots.txt pointing crawlers to the sitemap."""
    base = "https://fake-news-detector-8djq.onrender.com"
    return PlainTextResponse(
        f"User-agent: *\nAllow: /\nAllow: /claim/\nAllow: /about\nAllow: /privacy\nDisallow: /api/\nDisallow: /dashboard\nDisallow: /settings\nDisallow: /batch\n\nSitemap: {base}/sitemap.xml\n",
        headers={"Cache-Control": "public, max-age=86400"})


@router.get("/api/v1/claim/{claim_hash}/jsonld")
def claim_jsonld(claim_hash: str):
    """Return ClaimReview JSON-LD structured data for Google's fact-check panel."""
    claim = get_seo_claim(claim_hash)
    if not claim:
        raise HTTPException(404, "Claim not found")

    verdict = claim.get("verdict", "UNVERIFIABLE")
    text = claim.get("claim_text", claim.get("text", ""))
    base_url = "https://fake-news-detector-8djq.onrender.com"

    rating_map = {
        "LIKELY_TRUE": {"name": "True", "val": 4, "best": 5, "worst": 1},
        "LIKELY_FALSE": {"name": "False", "val": 1, "best": 5, "worst": 1},
        "MIXED": {"name": "Mixture", "val": 3, "best": 5, "worst": 1},
        "UNVERIFIABLE": {"name": "Unverifiable", "val": 3, "best": 5, "worst": 1},
    }
    rating = rating_map.get(verdict, rating_map["UNVERIFIABLE"])

    jsonld = {
        "@context": "https://schema.org",
        "@type": "ClaimReview",
        "url": f"{base_url}/claim/{claim_hash}",
        "claimReviewed": text[:500],
        "author": {
            "@type": "Organization",
            "name": "VerifAI",
            "url": base_url,
        },
        "reviewRating": {
            "@type": "Rating",
            "ratingValue": rating["val"],
            "bestRating": rating["best"],
            "worstRating": rating["worst"],
            "alternateName": rating["name"],
        },
        "itemReviewed": {
            "@type": "Claim",
            "name": text[:200],
            "appearance": {
                "@type": "CreativeWork",
                "url": f"{base_url}/claim/{claim_hash}",
            },
        },
    }
    return jsonld
