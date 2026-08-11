"""
P3-3 Router Split — Scaffolding

This package defines the target router structure for the api.py modularization.
The actual routes are still in api.py. Migration should be done incrementally:

1. auth.py       — signup, login, logout, /me, google oauth (lines 332–608)
2. analyze.py    — /analyze, /batch, /compare, /smart-verify (lines 778–1500)
3. claims.py     — SEO claim pages, cards, JSON-LD, sitemap (lines 1721–2070)
4. history.py    — /user/history, /user/stats, /feedback, /share (lines 2688–3095)
5. telegram.py   — webhook, voice transcription (lines 2192–2460)
6. admin.py      — /health, /info, /admin/stats, /admin/metrics (lines 714–777, 3098–3190)
7. verify.py     — /fact-check, /safe-browsing, /source-credibility, /india-threat-scan (lines 1363–2190)

Each router should:
  - Import `APIRouter` from `fastapi`
  - Import shared state from `api` (model, tfidf, scaler, limiter, claim_cache)
  - Import helpers from `routers.deps`
  - Use `router = APIRouter(prefix="/api/v1", tags=["..."])`

Migration order (by coupling, easiest first):
  1. admin.py (fewest dependencies)
  2. auth.py (self-contained, no model deps)
  3. claims.py (depends on claim_cache only)
  4. history.py (depends on auth helper only)
  5. telegram.py (depends on _run_smart_verify)
  6. verify.py (depends on model + external APIs)
  7. analyze.py (deepest coupling — model, tfidf, scaler, OOD, meta features)
"""
