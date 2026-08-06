# VerifAI — Remediation Plan

Fix plan for every problem raised in the deep-analysis session (`read.txt`).
Each item was re-verified against the current working tree before being written up;
where verification changed the finding, that is called out explicitly.

**Status legend:** ✅ confirmed · ⚠️ confirmed + worse than reported · ❌ disproven · 🔍 needs your input

---

## Verification summary — what changed vs. `read.txt`

The original session was blocked from running `git` mid-analysis and had to hedge several
claims. Those are now resolved:

| Finding | Original claim | Verified reality |
|---|---|---|
| `.env` in git history | "could not confirm — treat as urgent" | ✅ **Confirmed leaked.** Present in `3b5c6b3`, `441da0f`; removed in `c9fd2a4` |
| Which keys leaked | "8+ live keys (Groq, GNews, Google, Telegram)" | ✅ **Narrower — 4 secrets:** `GEMINI_API_KEY`, `GNEWS_API_KEY`, `API_KEYS`, `DATABASE_URL`. **Groq, Google FactCheck, Google Safe Browsing, and Telegram keys were never committed** |
| `users.db` committed | "same concern, 81 KB with bcrypt hashes" | ❌ **Disproven.** Never tracked. No user credentials leaked |
| `analysis_history.db` committed | "same concern" | ✅ **Confirmed.** In `3b5c6b3`, `441da0f`; removed in `70df62a` |
| SEO page XSS | "narrow path via `verdict`" | ⚠️ **Worse.** A second, wide-open sink was missed — see P1-3 |
| Route count | "~45 route definitions" | ✅ 43 |
| `.dockerignore` | "missing" | ✅ Confirmed absent |

**Net effect on priority:** the secret exposure is real but *smaller* than feared (no password
hashes, no Groq/Google/Telegram keys). The XSS is *larger* than reported and is now the most
urgent code-level fix.

---

# Phase 0 — Containment (do today, before any other work)

## P0-1 ✅ Rotate the four leaked secrets

Confirmed exposed in git history and present in every clone and fork of this repo.

| Secret | Where to rotate |
|---|---|
| `GEMINI_API_KEY` | Google AI Studio → API keys → delete + recreate |
| `GNEWS_API_KEY` | gnews.io dashboard → regenerate |
| `API_KEYS` | Self-issued. Generate new values, update Render env + any client using them |
| `DATABASE_URL` | If it contains a live Postgres password, rotate that role's password in Render/Neon |

**Do not skip `API_KEYS`** — it is the app's own auth credential for the REST API
(`key:user` pairs), so a leaked value is a direct authentication bypass, not a third-party
billing risk.

Verify the leaked values are dead:

```bash
# Should return 401/403 with the OLD key
curl -s -o /dev/null -w "%{http_code}\n" \
  "https://gnews.io/api/v4/search?q=test&apikey=<OLD_GNEWS_KEY>"
```

## P0-2 ✅ Purge `.env` and `analysis_history.db` from git history

```bash
pip install git-filter-repo
cd "D:/fake news detector"
git clone --mirror . ../verifai-backup.git      # backup first — this is destructive

git filter-repo --invert-paths \
  --path .env \
  --path analysis_history.db \
  --force

git remote add origin <your-remote-url>          # filter-repo drops remotes
git push --force --all
git push --force --tags
```

Then confirm the objects are gone:

```bash
git log --all --oneline -- .env analysis_history.db   # must print nothing
git rev-list --all --objects -- .env                  # must print nothing
```

**Caveats to plan around:**
- Force-push rewrites every commit hash. Any collaborator must re-clone, not pull.
- **Forks and GitHub's cached views retain the old objects.** After force-pushing, open a
  GitHub support request to purge stale refs, and delete any forks you control.
- Rotation (P0-1) is what actually protects you. History purge is cleanup. **Do P0-1 first.**

## P0-3 Stop the bleeding structurally

`.gitignore` already lists `.env` and `*.db`, so nothing new will be added. Add a pre-commit
guard so it cannot regress:

```bash
pip install detect-secrets
detect-secrets scan > .secrets.baseline
```

`.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.5.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
```

---

# Phase 1 — Security fixes

## P1-1 ✅ Hash session tokens at rest

**Where:** `api.py:359-361` (signup), plus the login path and `auth.py` lookup.

Tokens are generated with `secrets.token_urlsafe(32)` and stored raw in `sessions.token`
with a 7-day TTL. Any read-only DB disclosure yields directly usable sessions for every
logged-in user.

**Fix** — store the hash, return the plaintext to the client only:

```python
import hashlib

def _hash_token(tok: str) -> str:
    return hashlib.sha256(tok.encode()).hexdigest()

# --- issue (signup + login) ---
token = secrets.token_urlsafe(32)
c.execute(
    f"INSERT INTO sessions (token, user_id, expires_at) VALUES ({ph(3)})",
    (_hash_token(token), user_id, expires_at),   # store hash
)
return {"token": token}                          # return plaintext

# --- validate (auth.py / _get_user_from_token) ---
c.execute(f"SELECT user_id, expires_at FROM sessions WHERE token = {ph()}",
          (_hash_token(presented_token),))
```

Plain SHA-256 (not bcrypt) is correct here: the token is already 256 bits of entropy, so it
is not brute-forceable and does not need a slow KDF.

**Migration:** existing rows hold plaintext and will stop validating. Either accept a forced
re-login (simplest, recommended) or run a one-time `UPDATE sessions SET token = sha256(token)`.
Grep for every `sessions.token` read before shipping — a missed call site silently logs
everyone out.

## P1-2 ✅ Constant-time Telegram webhook comparison

**Where:** `api.py:2163`

```python
# Before — comment claims "Constant-time-ish"; `!=` on str short-circuits
if not expected or secret != expected or header_secret != expected:

# After
if (not expected
        or not secrets.compare_digest(secret, expected)
        or not secrets.compare_digest(header_secret, expected)):
```

Low severity (network jitter makes remote timing attacks impractical), but the codebase
already uses `compare_digest` correctly at `api.py:720` and `api.py:2925` — this is an
inconsistency, and the misleading comment is worse than the bug. Delete the comment.

## P1-3 ⚠️ Stored XSS in the SEO claim pages — **two sinks, one missed by the original analysis**

**Where:** `api.py:1740-1783`

### Sink A — `verdict` unescaped in `title` (as reported)

`text` and `analysis` are escaped at lines 1734-1735. `verdict` is not, and `title` embeds it,
then flows into 8 attribute contexts plus `<h1>{title}</h1>`. Exploitation requires prompt-
injecting the Groq output past the whitelist at `api.py:1054-1058` — narrow but real, since
the article text is fully attacker-controlled.

### Sink B — JSON-LD `</script>` breakout — **NEW, and far more serious**

```python
"claimReviewed": text[:500],          # api.py — UNESCAPED `text`, not `safe_text`
"itemReviewed": {..., "name": text[:200]},
...
<script type="application/ld+json">{jsonld}</script>
```

`json.dumps` escapes `"` and `\` but **not `/`**. A claim containing `</script><script>…`
terminates the JSON-LD block and executes. This needs **no prompt injection** — the claim text
is directly attacker-controlled, so it is a one-step stored XSS on a stable public URL served
to search engines and social crawlers.

### Fix — escape at interpolation, not at read

```python
# 1. Whitelist verdict at the point of STORAGE (save_seo_claim, api.py:1200)
VALID_VERDICTS = {"LIKELY_TRUE", "LIKELY_FALSE", "MIXED", "UNVERIFIABLE"}
verdict = verdict if verdict in VALID_VERDICTS else "UNVERIFIABLE"

# 2. Escape everything at the point of INTERPOLATION
safe_verdict = html_mod.escape(claim.get("verdict", "UNVERIFIABLE").replace("_", " "))
title = html_mod.escape(f"VerifAI: {safe_verdict} ({confidence:.0f}% confidence)", quote=True)

# 3. Neutralise the JSON-LD breakout
jsonld = json_mod.dumps({...}).replace("<", "\\u003c").replace(">", "\\u003e")
```

The `\u003c` escape is the standard defence — it is valid JSON, parses identically, and cannot
close the tag.

### Also add a real CSP

`api.py:207` sets only `frame-ancestors`, `base-uri`, `object-src` — **no `script-src`**, so
it does not mitigate this at all. Add:

```
Content-Security-Policy: default-src 'self'; script-src 'self'; object-src 'none';
                         base-uri 'none'; frame-ancestors 'none'
```

JSON-LD in a `<script type="application/ld+json">` block is *data*, not script, so `script-src
'self'` does not break it.

**Regression test to add:**

```python
def test_claim_page_escapes_script_breakout():
    r = client.get(f"/claim/{hash_of('</script><script>alert(1)</script>')}",
                   headers={"User-Agent": "Twitterbot"})
    assert "</script><script>" not in r.text
```

## P1-4 ✅ SSRF — restrict ports

`backend/ssrf.py` is genuinely above average: full private/link-local blocklist including
`169.254.0.0/16` for cloud metadata (line 21), and `safe_get` (line 81) disables auto-redirects
and re-validates every hop (line 112) — the bypass most implementations miss. The DNS-rebinding
TOCTOU is honestly documented at lines 89-92. **Leave that design alone.**

Two real gaps:

```python
# Gap 1 — no port restriction; http://public-host:22/ currently passes
ALLOWED_PORTS = {80, 443, 8080, 8443}
port = parsed.port or (443 if parsed.scheme == "https" else 80)
if port not in ALLOWED_PORTS:
    raise ValueError(f"Port {port} not allowed")

# Gap 2 — line 66 defaults to 443 even for http:// URLs, so getaddrinfo
# resolves against the wrong port. Use the scheme-aware default above.
socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
```

## P1-5 ✅ Narrow the browser extension's permissions

**Where:** `extension/manifest.json:32`

`content.js` is injected on `<all_urls>` at `document_idle`, on top of `activeTab` +
`scripting`. If the extension only acts on right-click, drop the always-on content script:

```jsonc
// Remove the "content_scripts" block entirely, then inject on demand:
chrome.contextMenus.onClicked.addListener((info, tab) => {
  chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ["content.js"] });
});
```

This keeps behaviour identical, removes a persistent all-sites footprint, and avoids Chrome
Web Store review friction.

---

# Phase 2 — ML integrity (the headline problem)

> The single biggest issue in this project: **94.77% claimed, ~70% observed on fresh text.**
> Everything in this phase is about closing that gap honestly.

## P2-1 ✅ Delete the WelFake "cross-domain" claim — it is evaluation on training data

**Verified unambiguously:**
- `train.py:157-182` loads `data_new/WELFake_Dataset.csv`
- `train.py:316-320` appends it to the training pool
- `models/config.json:38-46` lists `"WELFake"` in `datasets_used`
- `eval_welfake.py:31` loads **the same CSV**, samples 5,000 rows (lines 64-66), scores the
  production model
- `eval_welfake.py:27` prints `"Testing production model on 72,134 unseen articles"`

The articles were seen during training. The numbers are meaningless.

**Action — delete, do not caveat:**
- `README.md:176-182` — remove the entire "Cross-Domain: WelFake Dataset" section, including
  the 97.72% accuracy and the 99.97% high-confidence figure.
- `eval_welfake.py` — either delete the script or fix line 27's false claim and rename it
  `eval_welfake_in_sample.py` so it can never be mistaken for a generalisation test.

This is the fix that matters most reputationally. It is the kind of error that discredits an
otherwise strong project the moment an informed reviewer spots it.

## P2-2 ✅ Re-split by source group, then retrain and publish whatever falls out

**Where:** `train.py:449-454`

```python
# Current — random split over a source-confounded pool
idx_temp, idx_test, y_temp, y_test = train_test_split(
    indices, y, test_size=0.15, stratify=y, random_state=42
)
```

In ISOT, **every** REAL article is Reuters and **every** FAKE article is from a handful of
partisan blogs. A random split puts articles from the same source — often the same event,
sometimes the same story rewritten on both sides — on both sides of the split. The model
learns *which outlet wrote this*, and the test set rewards it.

`train.py:367-379` already strips Reuters/AP/AFP datelines, with the comment *"TF-IDF learns
source style rather than veracity."* That is the right instinct but only removes the most
literal tell — vocabulary, topic distribution, house style, and era still separate the sources.
**Only a grouped or temporal split fixes a source-confounded split.**

```python
from sklearn.model_selection import StratifiedGroupKFold

groups = df["source_dataset"].astype(str)          # already populated at train.py:172
# Better if you have it: groups = df["source_dataset"] + "_" + df["domain"]

sgkf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
train_idx, test_idx = next(sgkf.split(indices, y, groups=groups))
```

If publication dates are available, a **temporal** split (train on older, test on newer) is
even more honest and matches deployment reality.

**Expect the number to drop well below 94.77%.** The ~70% in
`scratch_domain_test_output.json` is closer to the truth. Publish the real number.
**A defensible 80% beats an indefensible 95%.**

## P2-3 ✅ Fix the `NUM` token bug — verified line by line

**Where:** `utils.py:35, 48, 51`

```python
text = str(text).lower()                                  # line 35 — lowercases
text = re.sub(r'\b\d+(?:[.,]\d+)*%?\b', ' NUM ', text)    # line 48 — inserts UPPERCASE "NUM"
text = re.sub(r"[^a-z\s\-]", " ", text)                   # line 51 — deletes N, U, M
```

Line 51's character class is lowercase-only, so it strips the very token line 48 just
inserted. **Every number is silently deleted.** The comment on line 50 says *"keep letters,
spaces, hyphens, and NUM"* — it does not.

`README.md:108` advertises *"NUM Token Masking: Numbers normalized to `<NUM>` tokens during
preprocessing to preserve sentence structure."* **That feature has never worked.**

```python
# Fix — one character class
text = re.sub(r"[^a-zA-Z\s\-]", " ", text)
```

Two things to be precise about:

1. **This is not train/serve skew.** The bug is identical in training and inference, so the
   model is self-consistent. It is *discarded signal*, not corruption — dates, statistics, and
   counts are erased in a task where numeric specificity is a known real-vs-fake discriminator.
2. **The fix invalidates the current artifacts.** TF-IDF was fitted on the broken output.
   `model.joblib` / `tfidf.joblib` / `scaler.joblib` must be regenerated.

**Therefore: bundle P2-2 and P2-3 into a single retrain.** Do not ship them separately.

Also note `utils.py:62` filters on `tok.is_alpha`, which keeps `NUM` (alphabetic) — good — but
line 69's fallback requires `len(word) > 2`, and `"NUM"` is exactly 3 chars, so it survives.
Confirm with a unit test:

```python
def test_num_token_survives_cleaning():
    assert "NUM" in clean_text("The company reported 45 percent growth in 2024")
```

## P2-4 ✅ Harden the ensemble construction

**Where:** `train.py:603-615`

```python
voting_clf.estimators_ = [lr_best, rf_clf, sgd_clf, svc_clf, lgbm_clf]
voting_clf.le_ = _le
voting_clf.classes_ = np.array([0, 1])
```

This hand-assigns sklearn private attributes to fake a fitted state. It works, but depends on
sklearn's internal layout, and `requirements.txt:2` pins `scikit-learn==1.8.0` with
version-locked joblib artifacts. A minor bump can silently change `predict_proba` behaviour or
fail to unpickle.

Keeping the workaround is reasonable (`train.py:588-591` explains Stacking was dropped for
speed). Add a **load-time assertion** so a silent break becomes a loud one:

```python
# After building the ensemble in train.py, and again at model load in api.py
_probe = calibrated.predict_proba(X_val[:5])
assert _probe.shape == (5, 2), f"Ensemble shape regression: {_probe.shape}"
assert np.allclose(_probe.sum(axis=1), 1.0), "predict_proba rows must sum to 1"
assert list(calibrated.classes_) == [0, 1], "class order changed"
```

Also record the sklearn version in `models/config.json` and warn on mismatch at load.

## P2-5 ✅ Fix the stale ensemble label

`train.py:676` logs `"model": "Stacking (LR+RF+SGD+SVC+LGBM)..."` — it is a `VotingClassifier`.
`models/config.json:8` already says `"VotingClassifier (LR+RF+SGD+SVC+LGBM) + Meta"` correctly.
One-word fix; do it in the same commit as the retrain.

## P2-6 ✅ Investigate the false-positive bias and the dead OOD detector

`scratch_domain_test_output.json` is the most valuable file in the repo — the only test on
genuinely fresh text. 7 PASS / 3 FAIL (70%). **All three failures are real articles
misclassified as FAKE** — clinical research, astronomy, entertainment — at confidences of
50.0, 51.5, 50.0.

Two distinct problems:

**(a) Confidence of exactly 50.0 means zero ensemble signal.** The threshold (0.552,
`config.json:2`) then breaks the tie toward FAKE. For a misinformation tool, **flagging real
journalism as fake is the more damaging error.** Add an explicit abstention band:

```python
if 0.45 <= real_prob <= 0.60:
    prediction, confidence_tier = "UNCERTAIN", "Insufficient signal"
```

Surface this in the UI as "not enough signal to judge" rather than a FAKE verdict.

**(b) Every `ood_score` is 0.0 across all ten samples** — OOD detection was not engaged in that
harness. Trace `ood_detector.py` through the `analyze_article` path and confirm it is actually
called and its output is actually used. A feature that always returns 0.0 is either dead code
or a silently swallowed exception.

## P2-7 🔍 Decide what the README should claim

After the honest retrain, replace the performance table with:

| Metric | Value | How measured |
|---|---|---|
| Accuracy (grouped split) | *from P2-2* | `StratifiedGroupKFold` by source dataset — no source leakage |
| Accuracy (fresh text) | ~70% | 10 hand-written unseen samples, `scratch_domain_test_output.json` |
| Known weakness | FP bias | Real science/entertainment reporting can be flagged FAKE at ~50% confidence |

Stating the weakness openly is what separates a credible project from an overclaiming one.

---

# Phase 3 — Architecture and concurrency

## P3-1 ✅ Get inference and DB calls off the event loop

**The most impactful non-security defect.** `analyze_article` is `async def` (`api.py:761`) and
calls, directly on the loop:

- `clean_text` → spaCy NLP (`utils.py:58`)
- `tfidf.transform`
- `model.predict_proba` — five models including a 100-tree RF and 200-estimator LightGBM
- `get_db()` → synchronous `sqlite3`/`psycopg2` (`api.py:837`)
- `_get_user_from_token` → another sync DB round-trip (`api.py:829`)

In FastAPI a `def` handler runs in a threadpool, but an `async def` handler runs **on the
loop** — so every prediction stalls the entire server for its full duration. Under concurrent
load the app serialises completely.

`db.py:35-37` even comments *"FastAPI runs sync DB calls in a threadpool"* to justify
`ThreadedConnectionPool` — true for `def` handlers, but these are `async def`. **The pool is
correctly chosen for a threading model the app does not use.**

```python
from starlette.concurrency import run_in_threadpool

def _predict_sync(text: str):
    cleaned = clean_text(text)
    tfidf_features = tfidf.transform([cleaned])
    meta = compute_meta_features(re.sub(r'\s+', ' ', text).strip()).reshape(1, -1)
    features = hstack([tfidf_features, scaler.transform(meta)])
    return model.predict_proba(features)[0]

# In the async handler
proba = await run_in_threadpool(_predict_sync, text)
user_id = await run_in_threadpool(_get_user_from_token, request)
await run_in_threadpool(_save_analysis, user_id, preview, prediction, ...)
```

**`/batch` (`api.py:2499-2514`) is worse** — up to 50 sequential inferences on the loop.
Vectorise instead of looping, then hand the whole thing to one threadpool call:

```python
def _predict_batch_sync(texts: list[str]):
    cleaned = [clean_text(t) for t in texts]
    features = hstack([tfidf.transform(cleaned), scaler.transform(np.vstack(metas))])
    return model.predict_proba(features)          # ONE call for all 50

probas = await run_in_threadpool(_predict_batch_sync, [a.safe_text for a in batch.articles])
```

This is both a concurrency fix and a large batch-latency win — one `predict_proba` over 50 rows
is far cheaper than 50 calls over 1 row.

**Verify with a load test** before/after:

```bash
ab -n 100 -c 10 -p payload.json -T application/json http://localhost:8000/api/v1/analyze
```

## P3-2 ✅ Unwrap the module-level `else:` block

**Where:** `api.py:56-60` — the entire ~2,980-line application is indented inside `else:`.

```python
if not FASTAPI_AVAILABLE:
    class DummyApp: pass
    app = DummyApp()
else:
    # ~2,980 lines
```

This forces module state into a closure, makes routes untestable in isolation, defeats most
static analysis, and is the direct reason `api.py` is 3,046 lines. The graceful-degradation
intent is misplaced — **if FastAPI is not installed, crashing loudly is correct.**

```python
try:
    from fastapi import FastAPI, HTTPException, Request
except ImportError as e:
    raise SystemExit("FastAPI is required. Install with: pip install -r requirements.txt") from e

# ... 2,980 lines now at module level, unindented
```

Do this as a **pure dedent with zero logic changes**, in its own commit, so the diff is
reviewable and `git blame` stays useful.

## P3-3 ✅ Split `api.py` into routers

`backend/` shows the author already knows how to modularise — `ssrf.py`, `cache.py`, `db.py`,
`auth.py` are clean, focused, well-documented modules. `api.py` just never got the same
treatment. **Highest-leverage refactor available**, and much easier once P3-2 lands.

```
routers/
  auth.py        # signup, login, google oauth, sessions
  analyze.py     # analyze, batch, compare
  claims.py      # SEO claim pages, cards, JSON-LD
  history.py     # user history, bookmarks, feedback
  telegram.py    # webhook
  admin.py       # health detail, metrics
```

```python
# api.py becomes a thin composition root
from routers import auth, analyze, claims, history, telegram, admin
for r in (auth, analyze, claims, history, telegram, admin):
    app.include_router(r.router, prefix="/api/v1")
```

## P3-4 ✅ Remove the unused `requests` import

`api.py:40` still imports `requests` alongside `httpx`, despite the "all async I/O" claim.
Remove it — and note it is also referenced by the Dockerfile healthcheck (see P4-4), which is
a separate bug that must be fixed at the same time.

## P3-5 ❌ In-memory state — no action, document only

`_failed_logins` (`api.py:261`) and the cache are per-process and will not survive horizontal
scaling. **This is already honestly documented at `api.py:258-259`** and is correct for a
single Render instance.

`backend/cache.py` is solid — proper `threading.Lock`, TTL, LRU eviction, and `deepcopy` on
read to prevent mutation (line 40). The README's "160x speedup" is plausible for a cache hit
vs. two network calls.

**No change needed.** If you ever scale to multiple instances, move both to Redis — add that
as a note in the README's deployment section, not as a code change now.

---

# Phase 4 — Frontend, tests, ops

## P4-1 ✅ Lazy-load or drop Spline

`landing-page/package.json:18-19` pulls in `@splinetool/react-spline` + `@splinetool/runtime`
— a full 3D scene runtime. The Android build assets confirm it drags in
gaussian-splat-compression, physics, navmesh, opentype, and howler (an *audio* engine).

**Multiple MB of 3D/audio engine shipped to users of a text-classification app**, on a Render
free tier, much of it to mobile. Almost certainly the single biggest perf win available.

```tsx
const Spline = lazy(() => import('@splinetool/react-spline'));

<Suspense fallback={<StaticHeroImage />}>
  {!isMobile && <Spline scene="..." />}
</Suspense>
```

Measure first and after:

```bash
cd landing-page && npx vite-bundle-visualizer
```

If the hero is decorative, **deleting it outright is a defensible call** — a static image or
CSS gradient costs ~0 KB.

## P4-2 ✅ Collapse the duplicated page/component variants

Verified present:

```
pages/Dashboard.tsx  +  pages/desktop/DashboardDesktop.tsx  +  pages/mobile/DashboardMobile.tsx
pages/Analytics.tsx  +  pages/desktop/AnalyticsDesktop.tsx  +  pages/mobile/AnalyticsMobile.tsx
components/AppSidebar.tsx  +  components/desktop/AppSidebar.tsx
components/MobileNav.tsx   +  components/mobile/MobileNav.tsx
```

Three variants per page and two copies of two components — a copy-paste drift pattern where
fixes land in one variant and not the others. `useIsMobile.ts` already exists; CSS-driven
responsive layout collapses most of this.

Migrate one page at a time (Dashboard first), diffing the three variants to find behaviour that
exists in only one — that divergence *is* the accumulated drift, and it needs a deliberate
decision, not a blind merge.

## P4-3 ✅ Make the model tests capable of failing

**Where:** `test_model_quality.py:191-207`

The test asserts against `models/config.json` — it re-reads the numbers the training run wrote,
so **it can never detect degradation, only a missing file.** It is tautological.

Worse, the fixture articles at lines 131-146 are **Reuters-prefixed** — testing exactly the
source artifact `train.py:367-379` tries to strip.

```python
# Replace with a frozen holdout the model has never seen, committed to the repo
HOLDOUT = Path("tests/fixtures/holdout_labeled.jsonl")   # ~200 hand-labeled, mixed sources

def test_accuracy_does_not_regress():
    acc = evaluate(model, load_jsonl(HOLDOUT))
    assert acc >= 0.75, f"Accuracy regressed to {acc:.2%} (floor 0.75)"

def test_no_false_positive_bias_on_real_science():
    """Guards the exact failure mode in scratch_domain_test_output.json."""
    reals = [s for s in load_jsonl(HOLDOUT) if s["label"] == "REAL"]
    fp_rate = sum(predict(s["text"]) == "FAKE" for s in reals) / len(reals)
    assert fp_rate <= 0.20, f"False-positive rate on real news: {fp_rate:.2%}"
```

Strip the Reuters prefixes from the fixtures, or the test measures the confound rather than the
model.

## P4-4 ✅ Docker: add `.dockerignore`, fix the healthcheck

**Confirmed:** no `.dockerignore` exists, and `Dockerfile:33` is `COPY . .` — which copies
`data_new/` (the CSVs, `data.h5`, and three `.zip` archives) into the image. **Likely a
multi-GB image for no reason.**

`.dockerignore`:

```
.git
.env*
*.db
data_new/
data/
landing-page/node_modules/
landing-page/dist/
android/
extension/
__pycache__/
*.pyc
.pytest_cache/
tests/
*.md
```

**Healthcheck bug** (`Dockerfile:44`): it runs `python -c "import requests; ..."` but `requests`
is **not in `requirements-deploy.txt`** — the healthcheck has been failing silently. Use stdlib:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"
```

The multi-stage build with a non-root user (`Dockerfile:24,40`) is good — keep it.

Verify: `docker build -t verifai . && docker images verifai` — expect a large drop.

## P4-5 ✅ Lint the whole codebase in CI

`.github/workflows/ci.yml:19` lints only 4 files:

```yaml
- run: ruff check --select E,F,W --ignore E501 api.py utils.py meta_features.py enhanced_features.py
```

`backend/` — the SSRF helper, the DB layer, the auth module, the security-critical code — is
**entirely unlinted**.

```yaml
- run: ruff check --select E,F,W,B,S --ignore E501 .
```

`S` enables `flake8-bandit` security rules. Expect an initial backlog; fix or explicitly
`# noqa` each one rather than narrowing the selector.

## P4-6 ✅ Add the missing high-risk tests

No tests exist for SSRF bypass, auth/session expiry, or the RAG pipeline — the three areas
where a regression is most costly.

```python
# tests/test_ssrf.py
@pytest.mark.parametrize("url", [
    "http://169.254.169.254/latest/meta-data/",   # cloud metadata
    "http://127.0.0.1:8000/admin",
    "http://[::1]/",
    "http://localhost:22",
    "http://public-host:22/",                      # port bypass — P1-4
    "file:///etc/passwd",
])
def test_ssrf_blocked(url):
    with pytest.raises(ValueError):
        validate_url(url)

def test_ssrf_redirect_revalidated(httpserver):
    """Public URL 302-ing to metadata IP must be caught on the second hop."""
    ...

# tests/test_auth.py
def test_expired_session_rejected(): ...
def test_token_stored_hashed_not_plaintext():      # guards P1-1
    signup(); row = db.execute("SELECT token FROM sessions").fetchone()
    assert len(row[0]) == 64 and all(c in "0123456789abcdef" for c in row[0])
```

## P4-7 ✅ Reconcile version drift

Verified four different versions in the tree:

| Location | Value |
|---|---|
| `pyproject.toml:7` | `8.1.0` |
| `api.py:23` | `"8.0"` |
| `README.md` footer | `9.0` |
| `models/config.json:37` | `20260605_190500` |

Pick one (`9.0.0`), set it in `pyproject.toml`, and have `api.py` read it rather than hardcode:

```python
from importlib.metadata import version
APP_VERSION = version("fake-news-detector")
```

Keep `models/config.json`'s version distinct and date-stamped — **model version and app version
are legitimately different things** and should not be unified.

## P4-8 ✅ Fix the license contradiction

`pyproject.toml:11` declares `license = {text = "MIT"}` while `LICENSE` is a custom
attribution-required license. These contradict, and **`pyproject.toml` is what package tooling
and GitHub's license detector read** — so the project currently advertises MIT terms you did
not intend to grant.

🔍 **Decide which you actually want**, then make both files agree. If you want the custom
attribution requirement:

```toml
license = {file = "LICENSE"}
```

## P4-9 ✅ Fix the empty package build

`pyproject.toml:61` sets `packages.find.include = ["src*"]` but **there is no `src/`
directory** — so the package builds empty.

```toml
[tool.setuptools.packages.find]
include = ["backend*", "routers*"]      # routers* after P3-3
```

Verify: `python -m build && tar -tzf dist/*.tar.gz | head -30`

## P4-10 ✅ Correct the README endpoint count

README claims 15 endpoints; **verified 43** route definitions in `api.py`. Either document all
43 (generate the list from the OpenAPI schema) or say "43 endpoints — see `/docs`".

---

# Execution order

Sequenced by dependency, not just severity.

| # | Item | Why here | Est. |
|---|---|---|---|
| 1 | **P0-1** Rotate 4 secrets | Nothing else matters until keys are dead | 30 min |
| 2 | **P0-2/3** Purge history, add pre-commit | Cleanup after rotation | 1 h |
| 3 | **P1-3** XSS (both sinks) + CSP | Publicly reachable, no auth needed, crawler-fetched | 2 h |
| 4 | **P2-1** Delete WelFake claims | README-only, zero risk, removes the most discrediting error | 20 min |
| 5 | **P1-1** Hash session tokens | Touches auth — do before router refactor moves the code | 2 h |
| 6 | **P1-2 / P1-4 / P1-5** Timing, ports, extension | Small, independent | 1 h |
| 7 | **P3-1** Off the event loop | Biggest correctness-under-load fix | 4 h |
| 8 | **P4-4** `.dockerignore` + healthcheck | Trivial, large payoff | 30 min |
| 9 | **P2-2 + P2-3** Grouped split **+** NUM fix → **one retrain** | Both invalidate artifacts — must be a single retrain | 1 day |
| 10 | **P2-4/5/6** Ensemble asserts, label, OOD + abstention | Depends on the retrain | 4 h |
| 11 | **P2-7 / P4-7/8/9/10** Docs, versions, license, packaging | Reflects the new honest numbers | 2 h |
| 12 | **P4-3 / P4-6** Real holdout tests, SSRF/auth tests | Locks in everything above | 1 day |
| 13 | **P4-5** Lint everything | Will surface a backlog — do after churn settles | 3 h |
| 14 | **P3-2** Dedent the `else:` block | Pure mechanical, own commit | 2 h |
| 15 | **P3-3** Split into routers | Largest refactor, needs green tests first | 2 days |
| 16 | **P4-1 / P4-2** Spline, deduplicate pages | Independent frontend track | 1–2 days |

**Two sequencing constraints that are easy to get wrong:**

- **P2-2 and P2-3 must be one retrain.** Both invalidate `model.joblib`/`tfidf.joblib`/
  `scaler.joblib`. Running them separately means training twice for no benefit.
- **P1-1 before P3-3.** Hashing session tokens touches auth code that the router split will
  relocate. Doing it first avoids re-resolving the same change across moved files.

---

# What is already good — do not "fix" these

The original analysis was right to say the security engineering is above the level this kind of
project usually reaches. Verified and worth protecting during refactors:

- **`backend/ssrf.py`** — redirect re-validation on every hop (line 112) is the bypass most
  implementations miss; the DNS-rebinding TOCTOU docstring (lines 89-92) documents a real
  limitation honestly instead of pretending it away.
- **No SQL injection anywhere in the audited paths.** `ph()` (`db.py:83`) is a genuinely clean
  solution to the SQLite/Postgres placeholder split. `/user/history` (`api.py:2594`) builds
  `where = f"user_id = {ph()}"` — the f-string interpolates only the *placeholder*, never user
  data. **No IDOR found.**
- **Auth hardening** — bcrypt with dummy-hash timing defence (`api.py:398-399`), per-email
  lockout complementing per-IP limits (`api.py:266-280`), and real cryptographic Google JWT
  verification with an **explicit refusal to fall back to unverified base64 decode**
  (`api.py:511-520`).
- **`backend/cache.py`** — correct locking, TTL, LRU, and `deepcopy` on read.
- **Docs disabled in production** (`api.py:120-124`); health detail gated behind a token
  (`api.py:714-723`).
- **Multi-stage Docker build with a non-root user** (`Dockerfile:24,40`).

The ML overclaiming is more of a shame than a scandal: `scratch_domain_test_output.json` shows
the honest test **was run and the failures were recorded**. The gap is between what was measured
and what went on the badge. Closing it costs one retrain and a README edit.
