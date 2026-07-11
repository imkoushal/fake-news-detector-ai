# Chrome Web Store — Submission Kit (VerifAI Fact Check)

Everything needed to publish `extension/`. Build the upload artifact with
`node build.mjs` (emits `dist/` with the localhost origin stripped), then zip `dist/`.

---

## 1. Listing copy

**Name** (≤ 45 chars)
`VerifAI — Fact Check`

**Summary / short description** (≤ 132 chars)
`Right-click any text to fact-check it with VerifAI — evidence-based misinformation and scam detection, with sources.`

**Category:** Productivity
**Language:** English

**Detailed description**
```
Stop misinformation where you read it. Select any headline, message, or claim on a
web page, right-click, and choose "Check with VerifAI" — you'll get an evidence-based
verdict without leaving the page.

VerifAI combines a machine-learning ensemble with retrieval-augmented fact-checking
(live news + LLM reasoning) to tell you whether a claim is likely real or fake, how
confident it is, and the evidence behind the call. It also flags common scam and
misinformation patterns, including India-specific WhatsApp-forward scams (UPI fraud,
fake government schemes, health hoaxes).

HOW IT WORKS
• Select text on any page → right-click → "Check with VerifAI" → an inline verdict
  card appears on the page.
• Or click the toolbar icon to paste a claim or pull the current selection.
• Each result links to a full claim page with the supporting evidence.

PRIVACY-FIRST
• Nothing is sent until you explicitly start a check.
• Only the text you choose is sent — never your browsing history or the pages you visit.
• No trackers, no ads, no cookies.

Built by Koushal Ray. 🔍 Verified by VerifAI.
```

**Single-purpose statement** (store review field)
```
The extension has one purpose: let the user fact-check a piece of text they select or
paste by sending that text to the VerifAI API and displaying the verdict.
```

**Permission justifications** (store review fields)
- `contextMenus` — adds the "Check with VerifAI" right-click item.
- `activeTab` + `scripting` — injects the verdict card into the current tab only after
  the user invokes a check.
- host access to `fake-news-detector-8djq.onrender.com` — sends the user's text to the
  VerifAI API to obtain a verdict.

**Data-use disclosures** (fill in the dashboard's Privacy tab)
- Collects **"Website content"** = the user-selected/pasted text, used solely to perform
  the requested fact-check. Not sold, not used for tracking, not for creditworthiness.
- Check: *does not sell/transfer data*, *not used for unrelated purposes*, *not used for
  creditworthiness*.

**Privacy policy URL:** host `PRIVACY.md` (see §4) and paste the public URL here.

---

## 2. Graphic assets

| Asset | Spec | Status |
|-------|------|--------|
| Store icon | 128×128 PNG | ✅ `icons/icon128.png` |
| Screenshot(s) | 1280×800 or 640×400 PNG/JPEG, ≥1 (up to 5) | ⬜ capture (see §3) |
| Small promo tile | 440×280 PNG/JPEG | ⬜ optional |
| Marquee promo | 1400×560 | ⬜ optional |

## 3. How to capture screenshots (do this manually)

1. `node build.mjs` isn't needed for dev — load the source folder unpacked
   (`chrome://extensions` → Developer mode → Load unpacked → select `extension/`).
2. Open a news article, select a bold claim, right-click → **Check with VerifAI**;
   screenshot the inline verdict card. Repeat with the toolbar popup.
3. Resize/pad each shot to exactly **1280×800**. Aim for 2–3: (a) right-click menu,
   (b) verdict card on a page, (c) toolbar popup with a result.

## 4. Privacy policy hosting (REQUIRED — this is the current blocker)

The store will not publish without a reachable privacy policy URL. Options, cheapest first:
- Add a `/privacy` route to the landing page SPA (`landing-page/src/pages`) rendering
  `PRIVACY.md`, deploy, use that URL. **Recommended** — on-brand, free.
- Or paste `PRIVACY.md` into a public GitHub Gist / repo file and use its raw URL.

## 5. Pre-upload checklist

- [x] PNG icons 16/32/48/128 generated and wired into `manifest.json`
- [x] `dist/` build strips the localhost host-permission
- [ ] Privacy policy hosted at a public URL (§4)
- [ ] 1–3 screenshots at 1280×800 (§3)
- [ ] `node build.mjs` → zip `dist/` → upload in the Chrome Web Store dashboard
- [ ] Pay the one-time $5 developer registration fee (if not already registered)
- [ ] Fill single-purpose + permission justifications + data-use disclosures (§1)

<sub>🔍 Verified by VerifAI — built by Koushal Ray.</sub>
