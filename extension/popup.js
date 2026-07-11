const $ = (id) => document.getElementById(id);
const API_BASE = globalThis.VERIFAI_API_BASE;

const VERDICTS = {
  LIKELY_TRUE:  { label: "Likely True",        color: "#16a34a", icon: "✅" },
  LIKELY_FALSE: { label: "Likely False",       color: "#dc2626", icon: "⚠️" },
  MIXED:        { label: "Mixed / Misleading", color: "#d97706", icon: "⚖️" },
  UNVERIFIABLE: { label: "Unverifiable",       color: "#6b7280", icon: "❓" },
};

const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function show(html) {
  const box = $("result");
  box.hidden = false;
  box.innerHTML = html;
}

function render(data) {
  const v = VERDICTS[data.verdict] || VERDICTS.UNVERIFIABLE;
  const conf = Number.isFinite(data.confidence) ? `<span class="conf">${data.confidence}% confidence</span>` : "";
  const cred = data.credibility ? `<div class="cred">${esc(data.credibility)} source credibility</div>` : "";
  const articles = (data.web && data.web.articles) || [];
  const evidence = articles.slice(0, 3).map((a) => `
    <li><a href="${esc(a.url)}" target="_blank" rel="noopener noreferrer">${esc(a.title)}</a>
    <span class="src">${esc(a.source)}</span></li>`).join("");
  const permalink = data.permalink
    ? `<a class="more" href="${esc(data.permalink)}" target="_blank" rel="noopener noreferrer">Read full report →</a>`
    : "";

  show(`
    <div><span class="badge" style="background:${v.color}">${v.icon} ${v.label}</span>${conf}</div>
    ${cred}
    <div class="analysis">${esc(data.analysis || "No detailed analysis available.")}</div>
    ${evidence ? `<div class="ev-title">Evidence</div><ul class="ev">${evidence}</ul>` : ""}
    ${permalink}`);
}

async function check() {
  const text = $("text").value.trim();
  if (text.length < 10) {
    show(`<div class="err">Enter at least 10 characters to verify.</div>`);
    return;
  }
  $("check").disabled = true;
  show(`<div class="loading"><span class="spinner"></span><span>Checking claim…</span></div>`);
  chrome.runtime.sendMessage({ type: "verify", text }, (resp) => {
    $("check").disabled = false;
    if (chrome.runtime.lastError || !resp) {
      show(`<div class="err">${esc(chrome.runtime.lastError?.message || "No response from VerifAI.")}</div>`);
    } else if (resp.ok) {
      render(resp.data);
    } else {
      show(`<div class="err">${esc(resp.error)}</div>`);
    }
  });
}

async function useSelection() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) return;
  try {
    const [{ result } = {}] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => String(window.getSelection() || ""),
    });
    if (result && result.trim()) {
      $("text").value = result.trim();
    } else {
      show(`<div class="err">No text selected on the page.</div>`);
    }
  } catch {
    show(`<div class="err">Can't read selection on this page.</div>`);
  }
}

$("check").addEventListener("click", check);
$("useSelection").addEventListener("click", useSelection);
$("text").addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") check();
});
