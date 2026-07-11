# VerifAI Browser Extension (Phase 9.3)

Right-click any selected text → **Check with VerifAI** → an inline verdict card appears on the page.
Or click the toolbar icon to paste a claim / pull the current page selection.

A thin adapter over the existing `POST /api/v1/smart-verify` endpoint — no server changes required.
(MV3 service workers with `host_permissions` bypass CORS.)

## Load it (unpacked, for dev / review)

1. Open `chrome://extensions` (or `edge://extensions`).
2. Toggle **Developer mode** on.
3. Click **Load unpacked** and select this `extension/` folder.
4. Select any text on a page → right-click → **Check with VerifAI**.

> If the extension is installed while a tab is already open, reload that tab once so the
> content script is present.

## Point it at local dev

Edit `config.js` and switch the active line to `http://localhost:8000`, then run the API
locally (`uvicorn api:app --port 8000`) and reload the extension.

## Files

| File | Role |
|------|------|
| `manifest.json` | MV3 manifest (context menu + toolbar popup + content script) |
| `config.js` | Single source of truth for the API base URL |
| `background.js` | Service worker: context menu + all network calls |
| `content.js` | Shadow-DOM verdict card injected into the page |
| `popup.html/.css/.js` | Toolbar popup for pasted / selected text |
| `icon.svg` | Popup logo (copy of the app favicon) |
| `icons/` | Raster PNG icons (16/32/48/128) for toolbar + store |
| `build.mjs` | Produces `dist/` for the Web Store (strips the localhost origin) |
| `STORE_LISTING.md` | Web Store submission kit (copy, assets, checklist) |
| `PRIVACY.md` | Privacy policy (must be hosted at a public URL before submission) |

## Building the store package

```
node build.mjs      # writes ./dist with host_permissions narrowed to production
```
Then zip `dist/` and upload it in the Chrome Web Store dashboard.
The source folder keeps the `localhost` host-permission so `Load unpacked` works
against a local API; `dist/` drops it.

### Regenerating the PNG icons (only if `icon.svg` changes)

```
npm install --no-save sharp
node -e "const s=require('sharp'),fs=require('fs');[16,32,48,128].forEach(n=>s('icon.svg',{density:384}).resize(n,n,{fit:'contain',background:{r:0,g:0,b:0,alpha:0}}).png().toFile('icons/icon'+n+'.png'))"
```

## Before Chrome Web Store submission

- [x] Add raster PNG icons (16/32/48/128) and wire `action.default_icon` + `icons` in the manifest.
- [x] Narrow `host_permissions` to production only for the published build (`node build.mjs`).
- [ ] Host `PRIVACY.md` at a public URL and add it to the listing (**required** — see `STORE_LISTING.md` §4).
- [ ] Capture 1–3 screenshots at 1280×800 (see `STORE_LISTING.md` §3).
- [ ] Fill single-purpose + permission justifications + data-use disclosures (see `STORE_LISTING.md` §1).

<sub>🔍 Verified by VerifAI — built by Koushal Ray.</sub>
