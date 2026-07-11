# VerifAI Browser Extension — Privacy Policy

_Last updated: 2026-07-11_

The VerifAI browser extension ("the extension") helps you fact-check text using the
VerifAI service. This policy explains exactly what the extension does with your data.

## What the extension sends

When **you** trigger a check — by selecting text and choosing **"Check with VerifAI"**,
or by pasting/submitting text in the toolbar popup — the extension sends **only that
text** (truncated to 3,000 characters) to the VerifAI API at
`https://fake-news-detector-8djq.onrender.com` so it can be verified.

Nothing is sent unless you explicitly start a check. The extension does **not**:

- read, collect, or transmit the pages you browse,
- track your browsing history, clicks, or activity,
- use cookies, analytics, fingerprinting, or advertising trackers,
- collect names, emails, passwords, payment info, health, or location data.

## What VerifAI does with the text

The submitted text is processed to produce a verdict (real/fake), a confidence score,
and supporting evidence. Verified claims may be cached and, for public claims, published
as an indexable claim page — this is the same behavior as using the VerifAI website. Do
not submit private or sensitive personal information for verification.

## Data retention and sharing

The extension itself stores nothing on your device beyond your configuration. The text
you submit is handled by the VerifAI service solely to return and cache a verdict. We do
**not** sell your data or share it with third parties for advertising.

## Permissions and why they are needed

- **contextMenus** — to add the "Check with VerifAI" right-click menu item.
- **activeTab / scripting** — to display the verdict card on the page you're viewing,
  only after you invoke a check.
- **host access to `fake-news-detector-8djq.onrender.com`** — to send your check to the
  VerifAI API and receive the result.

## Contact

Questions: Koushal Ray (VerifAI). Open an issue on the project repository.
