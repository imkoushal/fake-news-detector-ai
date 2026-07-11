// Single source of truth for the API base URL.
// For local development against `uvicorn api:app --port 8000`, switch to the localhost line.
// (host_permissions in manifest.json already allow both origins.)
globalThis.VERIFAI_API_BASE = "https://fake-news-detector-8djq.onrender.com";
// globalThis.VERIFAI_API_BASE = "http://localhost:8000";
