"""
Regression tests for the server-rendered claim pages (P1-3).

These pages are the only server-rendered HTML in the app and every value in them
comes from user-submitted article text, so each interpolation point gets a test.

History (do not delete these without reading it):
  * The JSON-LD block interpolated raw `claim_text` via json.dumps, which escapes
    `"` and `\\` but not `/`. A claim containing `</script><script>` closed the
    block and executed. Reproduced against the live handler before the fix.
  * `verdict` reached the page title, the <h1> and the SVG card's verdict label
    unescaped. Not reachable today because the LLM parser only ever assigns one
    of four literals, but a parser change would reopen all three at once.
  * The browser branch served an inline `location.replace('/claim/<hash>')` —
    the same URL it was served from — an infinite reload loop.
"""
import hashlib
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from api import app  # noqa: E402
from backend.claims_db import init_seo_claims_db, save_seo_claim  # noqa: E402

CRAWLER_UA = {"User-Agent": "Twitterbot/1.0"}
BROWSER_UA = {"User-Agent": "Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Chrome/120"}

BREAKOUT = "</script><script>alert(document.domain)</script>"


@pytest.fixture(scope="module")
def client():
    init_seo_claims_db()
    with TestClient(app) as c:
        yield c


def _store(text, verdict="LIKELY_FALSE", confidence=88.0, analysis="Test analysis."):
    """Persist a claim and return its hash."""
    claim_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
    save_seo_claim(claim_hash, text, {
        "verdict": verdict,
        "confidence": confidence,
        "analysis": analysis,
    })
    return claim_hash


class TestJsonLdBreakout:
    """Sink B — the one that was live."""

    def test_script_tag_cannot_close_jsonld_block(self, client):
        h = _store(f"Breaking news {BREAKOUT} story")
        r = client.get(f"/claim/{h}", headers=CRAWLER_UA)
        assert r.status_code == 200
        # The literal closing tag must not survive anywhere in the response.
        assert "</script><script>" not in r.text
        # Exactly one JSON-LD block, still terminated exactly once.
        assert r.text.count('<script type="application/ld+json">') == 1
        assert r.text.count("</script>") == 1

    def test_jsonld_still_parses_and_preserves_the_claim(self, client):
        """The escape must not corrupt the data — Google reads this block."""
        import json
        import re

        text = "Scientists say 5 > 3 & <b>bold</b> claims need review"
        h = _store(text)
        r = client.get(f"/claim/{h}", headers=CRAWLER_UA)
        block = re.search(
            r'<script type="application/ld\+json">(.*?)</script>', r.text, re.S
        )
        assert block, "JSON-LD block missing"
        data = json.loads(block.group(1))
        # < etc. decode back to the original characters.
        assert data["claimReviewed"] == text
        assert data["@type"] == "ClaimReview"

    def test_angle_brackets_are_unicode_escaped(self, client):
        h = _store("Claim with <tag> inside")
        r = client.get(f"/claim/{h}", headers=CRAWLER_UA)
        assert "\\u003c" in r.text and "\\u003e" in r.text


class TestVerdictSinks:
    """Sinks A and C — latent, guarded by clamping at read."""

    def test_hostile_verdict_is_clamped_not_rendered(self, client):
        h = _store("A normal claim", verdict='"><script>alert(1)</script>')
        r = client.get(f"/claim/{h}", headers=CRAWLER_UA)
        assert r.status_code == 200
        assert "<script>alert(1)" not in r.text
        assert "UNVERIFIABLE" in r.text

    def test_hostile_verdict_does_not_reach_the_svg_card(self, client):
        h = _store("A normal claim", verdict="</text><script>alert(1)</script>")
        r = client.get(f"/api/v1/claim/{h}/card.svg")
        assert r.status_code == 200
        assert "<script>" not in r.text

    def test_known_verdicts_survive_intact(self, client):
        """The clamp must not break the happy path."""
        for verdict, expected in [
            ("LIKELY_TRUE", "LIKELY TRUE"),
            ("LIKELY_FALSE", "LIKELY FALSE"),
            ("MIXED", "MIXED"),
        ]:
            h = _store(f"Claim about {verdict}", verdict=verdict)
            r = client.get(f"/claim/{h}", headers=CRAWLER_UA)
            assert expected in r.text, f"{verdict} was lost"

    def test_non_numeric_confidence_does_not_500(self, client):
        """Stored JSON is not schema-checked; a bad confidence must not crash."""
        h = _store("Claim with bad confidence", confidence="not-a-number")
        assert client.get(f"/claim/{h}", headers=CRAWLER_UA).status_code == 200
        assert client.get(f"/api/v1/claim/{h}/card.svg").status_code == 200


class TestClaimPageHeaders:
    def test_crawler_page_sets_script_blocking_csp(self, client):
        h = _store("A claim needing a CSP")
        csp = client.get(f"/claim/{h}", headers=CRAWLER_UA).headers.get(
            "content-security-policy", ""
        )
        # The app-wide policy has no script-src at all; this page must.
        assert "default-src 'none'" in csp
        assert "frame-ancestors 'none'" in csp

    def test_svg_card_sets_csp(self, client):
        h = _store("A claim needing a card CSP")
        csp = client.get(f"/api/v1/claim/{h}/card.svg").headers.get(
            "content-security-policy", ""
        )
        assert "default-src 'none'" in csp


class TestBrowserBranchDoesNotLoop:
    def test_no_self_redirect(self, client):
        """Guards the infinite reload loop: the page must not navigate to itself."""
        h = _store("A claim viewed in a browser")
        r = client.get(f"/claim/{h}", headers=BROWSER_UA)
        assert r.status_code == 200
        assert f"location.replace('/claim/{h}')" not in r.text
        assert "window.location.replace" not in r.text

    def test_serves_the_spa_with_og_tags(self, client):
        h = _store("A claim that should render in the SPA")
        r = client.get(f"/claim/{h}", headers=BROWSER_UA)
        assert 'property="og:title"' in r.text
        # SPA shell present when built, so React Router renders /claim/:hash.
        if (PROJECT_ROOT / "landing-page" / "dist" / "index.html").exists():
            assert 'id="root"' in r.text or "<div id=root" in r.text

    def test_browser_branch_escapes_claim_text(self, client):
        h = _store(f"Browser claim {BREAKOUT}")
        r = client.get(f"/claim/{h}", headers=BROWSER_UA)
        assert "</script><script>alert" not in r.text
