// Injected on every page (idle). Renders the verdict as a floating card in a
// Shadow DOM so the host page's CSS can never touch it. Idle until it hears
// from the service worker.
(() => {
  if (window.__verifaiInjected) return; // content scripts can double-run on some navigations
  window.__verifaiInjected = true;

  const HOST_ID = "verifai-card-host";

  const VERDICTS = {
    LIKELY_TRUE:  { label: "Likely True",        color: "#16a34a", icon: "✅" },
    LIKELY_FALSE: { label: "Likely False",       color: "#dc2626", icon: "⚠️" },
    MIXED:        { label: "Mixed / Misleading", color: "#d97706", icon: "⚖️" },
    UNVERIFIABLE: { label: "Unverifiable",       color: "#6b7280", icon: "❓" },
  };

  const esc = (s) =>
    String(s ?? "").replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  function ensureHost() {
    let host = document.getElementById(HOST_ID);
    if (host) return host.shadowRoot;
    host = document.createElement("div");
    host.id = HOST_ID;
    (document.body || document.documentElement).appendChild(host);
    const root = host.attachShadow({ mode: "open" });
    root.innerHTML = `<style>${STYLES}</style><div class="wrap"></div>`;
    return root;
  }

  function mount(html) {
    const root = ensureHost();
    root.querySelector(".wrap").innerHTML = html;
    const close = root.querySelector(".close");
    if (close) close.onclick = () => document.getElementById(HOST_ID)?.remove();
  }

  function shell(bodyHtml, accent = "#863bff") {
    return `
      <div class="card" style="--accent:${accent}">
        <div class="head">
          <span class="brand">🔍 VerifAI</span>
          <button class="close" title="Close">×</button>
        </div>
        ${bodyHtml}
        <div class="foot">Verified by VerifAI</div>
      </div>`;
  }

  function renderLoading(query) {
    mount(shell(`
      <div class="loading">
        <span class="spinner"></span>
        <span>Checking claim…</span>
      </div>
      <div class="query">${esc((query || "").slice(0, 140))}</div>`));
  }

  function renderError(error) {
    mount(shell(`
      <div class="verdict" style="--accent:#dc2626">
        <span class="badge" style="background:#dc2626">Couldn't verify</span>
      </div>
      <div class="analysis">${esc(error || "Something went wrong. Try again.")}</div>`,
      "#dc2626"));
  }

  function renderResult(data, query) {
    const v = VERDICTS[data.verdict] || VERDICTS.UNVERIFIABLE;
    const conf = Number.isFinite(data.confidence) ? `${data.confidence}%` : "";
    const cred = data.credibility ? `${data.credibility} source credibility` : "";

    const articles = (data.web && data.web.articles) || [];
    const evidence = articles.slice(0, 3).map((a) => `
      <li>
        <a href="${esc(a.url)}" target="_blank" rel="noopener noreferrer">${esc(a.title)}</a>
        <span class="src">${esc(a.source)}</span>
      </li>`).join("");

    const permalink = data.permalink
      ? `<a class="more" href="${esc(data.permalink)}" target="_blank" rel="noopener noreferrer">Read full report →</a>`
      : "";

    mount(shell(`
      <div class="verdict">
        <span class="badge" style="background:${v.color}">${v.icon} ${v.label}</span>
        ${conf ? `<span class="conf">${conf} confidence</span>` : ""}
      </div>
      ${cred ? `<div class="cred">${esc(cred)}</div>` : ""}
      <div class="analysis">${esc(data.analysis || "No detailed analysis available.")}</div>
      ${evidence ? `<div class="ev-title">Evidence</div><ul class="ev">${evidence}</ul>` : ""}
      ${permalink}`,
      v.color));
  }

  chrome.runtime.onMessage.addListener((msg) => {
    if (!msg || !msg.type) return;
    if (msg.type === "verifai_loading") renderLoading(msg.query);
    else if (msg.type === "verifai_result") renderResult(msg.data, msg.query);
    else if (msg.type === "verifai_error") renderError(msg.error);
  });

  const STYLES = `
    .wrap { all: initial; }
    * { box-sizing: border-box; }
    .card {
      position: fixed; top: 16px; right: 16px; width: 340px; max-height: 80vh; overflow-y: auto;
      z-index: 2147483647; background: #fff; color: #1a1a1a; border-radius: 14px;
      border-top: 4px solid var(--accent, #863bff);
      box-shadow: 0 12px 40px rgba(0,0,0,.22);
      font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      padding: 14px 16px 12px;
    }
    .head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
    .brand { font-weight: 700; color: #863bff; letter-spacing: .2px; }
    .close { border: 0; background: transparent; font-size: 22px; line-height: 1; cursor: pointer; color: #888; padding: 0 4px; }
    .close:hover { color: #1a1a1a; }
    .loading { display: flex; align-items: center; gap: 10px; font-weight: 600; }
    .spinner { width: 16px; height: 16px; border: 2px solid #ddd; border-top-color: #863bff; border-radius: 50%; display: inline-block; animation: verifai-spin .7s linear infinite; }
    @keyframes verifai-spin { to { transform: rotate(360deg); } }
    .query { margin-top: 8px; color: #666; font-size: 12px; font-style: italic; }
    .verdict { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 6px; }
    .badge { color: #fff; font-weight: 700; padding: 4px 10px; border-radius: 999px; font-size: 13px; }
    .conf { color: #555; font-size: 12px; font-weight: 600; }
    .cred { color: #777; font-size: 12px; margin-bottom: 8px; }
    .analysis { color: #333; margin: 6px 0 10px; }
    .ev-title { font-weight: 700; font-size: 12px; text-transform: uppercase; letter-spacing: .4px; color: #888; margin-bottom: 4px; }
    .ev { list-style: none; margin: 0 0 10px; padding: 0; }
    .ev li { margin-bottom: 6px; }
    .ev a { color: #4f46e5; text-decoration: none; display: block; font-weight: 600; }
    .ev a:hover { text-decoration: underline; }
    .ev .src { color: #999; font-size: 11px; }
    .more { display: inline-block; color: #863bff; font-weight: 700; text-decoration: none; font-size: 13px; }
    .more:hover { text-decoration: underline; }
    .foot { margin-top: 10px; padding-top: 8px; border-top: 1px solid #eee; color: #aaa; font-size: 11px; text-align: center; }
  `;
})();
