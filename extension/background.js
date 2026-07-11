// Service worker: owns the context menu and all network calls.
// MV3 service workers with host_permissions bypass CORS, so no server change is needed.
importScripts("config.js");

const API_BASE = globalThis.VERIFAI_API_BASE;

async function verify(text) {
  const res = await fetch(`${API_BASE}/api/v1/smart-verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: text.slice(0, 3000) }),
  });
  if (!res.ok) throw new Error(`VerifAI API returned ${res.status}`);
  return res.json();
}

// Attach the permalink to the full claim page so the UI can link to it.
function withPermalink(data) {
  const permalink = data && data.claim_hash ? `${API_BASE}/claim/${data.claim_hash}` : null;
  return { ...data, permalink };
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "verifai-check",
    title: "Check with VerifAI",
    contexts: ["selection"],
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId !== "verifai-check" || !info.selectionText || !tab?.id) return;
  const query = info.selectionText.trim();
  chrome.tabs.sendMessage(tab.id, { type: "verifai_loading", query });
  try {
    const data = withPermalink(await verify(query));
    chrome.tabs.sendMessage(tab.id, { type: "verifai_result", data, query });
  } catch (e) {
    chrome.tabs.sendMessage(tab.id, { type: "verifai_error", error: String(e.message || e) });
  }
});

// The popup verifies through here too, so networking lives in one place.
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg?.type === "verify") {
    verify(msg.text)
      .then((data) => sendResponse({ ok: true, data: withPermalink(data) }))
      .catch((e) => sendResponse({ ok: false, error: String(e.message || e) }));
    return true; // keep the message channel open for the async response
  }
});
