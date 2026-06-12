/* ===== Verify — Frontend App Logic ===== */
const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:8000'
  : window.location.origin;

// ===== AUTH STATE =====
let currentUser = null;
function getToken() { return localStorage.getItem('verify_token'); }
function setToken(t) { localStorage.setItem('verify_token', t); }
function clearToken() { localStorage.removeItem('verify_token'); }

function showAuthOverlay() {
  document.getElementById('authOverlay').classList.remove('hidden');
  document.getElementById('navbar').style.display = 'none';
  document.getElementById('profileWrap').classList.add('hidden');
}
function hideAuthOverlay() {
  document.getElementById('authOverlay').classList.add('hidden');
  document.getElementById('navbar').style.display = '';
  if (currentUser) {
    const avatarEl = document.getElementById('userAvatar');
    const dropAvatarEl = document.getElementById('dropdownAvatar');
    if (currentUser.avatar_url) {
      avatarEl.innerHTML = `<img src="${currentUser.avatar_url}" alt="" referrerpolicy="no-referrer">`;
      avatarEl.classList.add('has-img');
      dropAvatarEl.innerHTML = `<img src="${currentUser.avatar_url}" alt="" referrerpolicy="no-referrer">`;
      dropAvatarEl.classList.add('has-img');
    } else {
      const initial = currentUser.name.charAt(0).toUpperCase();
      avatarEl.textContent = initial;
      avatarEl.classList.remove('has-img');
      dropAvatarEl.textContent = initial;
      dropAvatarEl.classList.remove('has-img');
    }
    document.getElementById('dropdownName').textContent = currentUser.name;
    document.getElementById('dropdownEmail').textContent = currentUser.email || '';
    document.getElementById('profileWrap').classList.remove('hidden');
  }
}
async function checkSession() {
  const token = getToken();
  if (!token) { showAuthOverlay(); return; }
  try {
    const res = await fetch(API_BASE + '/api/v1/auth/me', { headers: { 'Authorization': 'Bearer ' + token } });
    if (!res.ok) throw new Error();
    currentUser = await res.json();
    hideAuthOverlay();
  } catch { clearToken(); showAuthOverlay(); }
}
async function handleLogin(e) {
  e.preventDefault();
  const errEl = document.getElementById('loginError');
  const btn = document.getElementById('loginBtn');
  errEl.classList.remove('show'); btn.textContent = 'Signing in...'; btn.disabled = true;
  try {
    const res = await fetch(API_BASE + '/api/v1/auth/login', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: document.getElementById('loginEmail').value, password: document.getElementById('loginPassword').value })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Login failed');
    setToken(data.token); currentUser = data.user; hideAuthOverlay();
    showToast('Welcome back, ' + currentUser.name + '!');
  } catch (err) { errEl.textContent = err.message; errEl.classList.add('show'); }
  btn.textContent = 'Sign In'; btn.disabled = false;
}
async function handleSignup(e) {
  e.preventDefault();
  const errEl = document.getElementById('signupError');
  const btn = document.getElementById('signupBtn');
  errEl.classList.remove('show'); btn.textContent = 'Creating account...'; btn.disabled = true;
  try {
    const res = await fetch(API_BASE + '/api/v1/auth/signup', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: document.getElementById('signupName').value, email: document.getElementById('signupEmail').value, password: document.getElementById('signupPassword').value })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Signup failed');
    setToken(data.token); currentUser = data.user; hideAuthOverlay();
    showToast('Welcome to Verify, ' + currentUser.name + '!');
  } catch (err) { errEl.textContent = err.message; errEl.classList.add('show'); }
  btn.textContent = 'Create Account'; btn.disabled = false;
}
async function handleLogout() {
  try { await fetch(API_BASE + '/api/v1/auth/logout', { method: 'POST', headers: { 'Authorization': 'Bearer ' + getToken() } }); } catch {}
  clearToken(); currentUser = null; showAuthOverlay(); showToast('Signed out');
}

// ===== GOOGLE AUTH =====
async function handleGoogleCredential(credential) {
  const errEl = document.getElementById('loginError');
  errEl.classList.remove('show');
  try {
    const res = await fetch(API_BASE + '/api/v1/auth/google', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ credential })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Google sign-in failed');
    setToken(data.token); currentUser = data.user; hideAuthOverlay();
    showToast('Welcome, ' + currentUser.name + '!');
  } catch (err) {
    errEl.textContent = err.message; errEl.classList.add('show');
  }
}

function initGoogleAuth() {
  // Fetch the Google Client ID from the backend config endpoint
  fetch(API_BASE + '/api/v1/auth/google-client-id')
    .then(r => r.json())
    .then(data => {
      if (!data.client_id) return; // Google OAuth not configured
      if (typeof google === 'undefined' || !google.accounts) {
        // GIS library not loaded yet, retry after a short delay
        setTimeout(initGoogleAuth, 500);
        return;
      }
      google.accounts.id.initialize({
        client_id: data.client_id,
        callback: (response) => handleGoogleCredential(response.credential),
        auto_select: false
      });
      // Wire up both Google buttons to trigger the popup
      document.getElementById('googleLoginBtn')?.addEventListener('click', () => {
        google.accounts.id.prompt();
      });
      document.getElementById('googleSignupBtn')?.addEventListener('click', () => {
        google.accounts.id.prompt();
      });
    })
    .catch(() => {}); // Silently ignore if endpoint not available
}

// ===== ROUTING =====
function navigate(page) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
  const el = document.getElementById('page-' + page);
  if (el) { el.classList.add('active'); }
  document.querySelectorAll(`[data-page="${page}"]`).forEach(l => l.classList.add('active'));
  window.scrollTo(0, 0);
  if (page === 'dashboard') initDashboard();
  if (page === 'history') loadHistory();
  // Close mobile menu
  document.getElementById('navLinks').classList.remove('open');
}

window.addEventListener('hashchange', () => {
  const page = location.hash.slice(1) || 'home';
  navigate(page);
});

document.addEventListener('DOMContentLoaded', () => {
  // Auth — check session first
  checkSession();

  // Auth form toggles
  document.getElementById('showSignup').addEventListener('click', () => {
    document.getElementById('loginPanel').classList.remove('active');
    document.getElementById('signupPanel').classList.add('active');
  });
  document.getElementById('showLogin').addEventListener('click', () => {
    document.getElementById('signupPanel').classList.remove('active');
    document.getElementById('loginPanel').classList.add('active');
  });
  document.getElementById('loginForm').addEventListener('submit', handleLogin);
  document.getElementById('signupForm').addEventListener('submit', handleSignup);
  document.getElementById('logoutBtn').addEventListener('click', handleLogout);

  // Initialize Google Auth
  initGoogleAuth();

  // Profile dropdown toggle
  document.getElementById('avatarBtn').addEventListener('click', (e) => {
    e.stopPropagation();
    document.getElementById('profileDropdown').classList.toggle('open');
  });
  // Close dropdown on outside click
  document.addEventListener('click', (e) => {
    const wrap = document.getElementById('profileWrap');
    if (wrap && !wrap.contains(e.target)) {
      document.getElementById('profileDropdown').classList.remove('open');
    }
  });
  // Close dropdown when a menu item is clicked
  document.querySelectorAll('.dropdown-item').forEach(item => {
    item.addEventListener('click', () => {
      document.getElementById('profileDropdown').classList.remove('open');
    });
  });

  const page = location.hash.slice(1) || 'home';
  navigate(page);

  // Nav link clicks
  document.querySelectorAll('[data-page]').forEach(el => {
    el.addEventListener('click', (e) => {
      const pg = el.dataset.page;
      if (el.tagName === 'BUTTON' || el.tagName === 'A') {
        if (!el.getAttribute('href')) {
          e.preventDefault();
          location.hash = pg;
        }
      }
    });
  });

  // Hamburger
  document.getElementById('hamburger').addEventListener('click', () => {
    document.getElementById('navLinks').classList.toggle('open');
  });

  // Theme toggle
  document.getElementById('themeToggle').addEventListener('click', toggleTheme);
  document.getElementById('settingsTheme')?.addEventListener('change', toggleTheme);

  // Char count
  const ta = document.getElementById('articleText');
  ta.addEventListener('input', () => {
    document.getElementById('charCount').textContent = ta.value.length + ' / 5000 chars';
  });

  // Analyze button
  document.getElementById('analyzeBtn').addEventListener('click', runAnalysis);

  // Feedback
  document.getElementById('submitFeedback')?.addEventListener('click', () => showToast('Thanks for your feedback!'));

  // ── Sensitivity Slider Tooltip (Analyze page) ──
  const slider = document.getElementById('sensitivitySlider');
  const tooltip = document.getElementById('sensitivityTooltip');
  if (slider && tooltip) {
    function updateTooltipPosition() {
      const val = slider.value / 100;
      tooltip.textContent = val.toFixed(2);
      // Position tooltip above thumb — map value to slider track width
      const pct = slider.value / slider.max;
      const thumbHalf = 8; // half of 16px thumb
      const trackWidth = slider.offsetWidth;
      const left = pct * (trackWidth - thumbHalf * 2) + thumbHalf;
      tooltip.style.left = left + 'px';
      tooltip.style.transform = 'translateX(-50%)';
    }
    slider.addEventListener('input', updateTooltipPosition);
    slider.addEventListener('mousedown', () => { updateTooltipPosition(); tooltip.classList.add('visible'); });
    slider.addEventListener('touchstart', () => { updateTooltipPosition(); tooltip.classList.add('visible'); }, { passive: true });
    slider.addEventListener('mouseup', () => tooltip.classList.remove('visible'));
    slider.addEventListener('mouseleave', () => tooltip.classList.remove('visible'));
    slider.addEventListener('touchend', () => tooltip.classList.remove('visible'));
    // Sync with settings slider
    slider.addEventListener('change', () => {
      const ss = document.getElementById('settingsSensitivity');
      if (ss) { ss.value = slider.value; document.getElementById('settingSensVal').textContent = (slider.value / 100).toFixed(2); }
    });
  }

  // ── Settings Sensitivity Slider (Settings page) — sync back ──
  const ss = document.getElementById('settingsSensitivity');
  if (ss) {
    ss.addEventListener('input', () => {
      document.getElementById('settingSensVal').textContent = (ss.value / 100).toFixed(2);
      const analyzeSlider = document.getElementById('sensitivitySlider');
      if (analyzeSlider) analyzeSlider.value = ss.value;
    });
  }

  // Batch upload
  setupBatch();

  // Filter pills (history)
  document.querySelectorAll('.filter-pills .pill').forEach(pill => {
    pill.addEventListener('click', () => {
      document.querySelectorAll('.filter-pills .pill').forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      loadHistory();
    });
  });

  // Upload zone drag
  const uz = document.getElementById('uploadZone');
  if (uz) {
    uz.addEventListener('dragover', e => { e.preventDefault(); uz.classList.add('dragover'); });
    uz.addEventListener('dragleave', () => uz.classList.remove('dragover'));
    uz.addEventListener('drop', e => { e.preventDefault(); uz.classList.remove('dragover'); handleFiles(e.dataTransfer.files); });
    uz.addEventListener('click', () => document.getElementById('csvFile').click());
  }

  // Typography scale buttons
  document.querySelectorAll('.btn-group [data-size]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.btn-group [data-size]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      document.documentElement.setAttribute('data-text-size', btn.dataset.size);
      localStorage.setItem('textSize', btn.dataset.size);
      showToast('Typography set to ' + btn.textContent.trim());
    });
  });

  // Restore saved text size
  const savedSize = localStorage.getItem('textSize');
  if (savedSize) {
    document.documentElement.setAttribute('data-text-size', savedSize);
    document.querySelectorAll('.btn-group [data-size]').forEach(b => {
      b.classList.toggle('active', b.dataset.size === savedSize);
    });
  }
});

// ===== THEME =====
function toggleTheme() {
  const html = document.documentElement;
  const isDark = html.getAttribute('data-theme') === 'dark';
  html.setAttribute('data-theme', isDark ? 'light' : 'dark');
  document.querySelector('.theme-icon').textContent = isDark ? '☀️' : '🌙';
}

// ===== TOAST =====
function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 3000);
}

// ===== URL INPUT TAB (2.2) =====
function switchInputTab(tab) {
  document.getElementById('tabText').classList.toggle('active', tab === 'text');
  document.getElementById('tabUrl').classList.toggle('active', tab === 'url');
  document.getElementById('inputText').classList.toggle('hidden', tab !== 'text');
  document.getElementById('inputUrl').classList.toggle('hidden', tab !== 'url');
}

async function fetchArticleFromUrl() {
  const url = document.getElementById('articleUrl').value.trim();
  if (!url) { showToast('Please enter a URL.'); return; }
  const btn = document.getElementById('fetchUrlBtn');
  const status = document.getElementById('urlStatus');
  btn.textContent = 'Fetching...';
  btn.disabled = true;
  status.textContent = 'Extracting article text from URL...';
  try {
    const res = await fetch(API_BASE + '/api/v1/fetch-url', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to fetch article');
    const ta = document.getElementById('articleTextFromUrl');
    ta.value = data.text;
    ta.classList.remove('hidden');
    // Also populate the main textarea so analysis works
    document.getElementById('articleText').value = data.text;
    status.textContent = `✅ Extracted ${data.word_count} words from: ${data.title || url}`;
    showToast('Article fetched! Click Analyze Article to continue.');
  } catch (e) {
    status.textContent = '❌ ' + e.message;
    showToast('Failed to fetch URL: ' + e.message);
  }
  btn.textContent = 'Fetch Article';
  btn.disabled = false;
}

// ===== FEEDBACK (2.5) =====
async function submitFeedback(articleText, modelPrediction, userCorrection) {
  const token = getToken();
  try {
    await fetch(API_BASE + '/api/v1/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...(token ? { 'Authorization': 'Bearer ' + token } : {}) },
      body: JSON.stringify({ text: articleText, model_prediction: modelPrediction, user_correction: userCorrection })
    });
    showToast('✅ Feedback submitted — thank you for helping improve the model!');
  } catch (e) {
    showToast('Could not submit feedback. Please try again.');
  }
}

// ===== ANALYZE =====
async function runAnalysis() {
  const text = document.getElementById('articleText').value.trim();
  const wordCount = text.split(/\s+/).filter(w => w.length > 0).length;
  if (!text || wordCount < 3) {
    showToast('Please enter at least a few words to analyze.');
    return;
  }

  const btn = document.getElementById('analyzeBtn');
  btn.textContent = 'Analyzing...';
  btn.disabled = true;

  let data;
  try {
    const headers = { 'Content-Type': 'application/json' };
    const token = getToken();
    if (token) headers['Authorization'] = 'Bearer ' + token;
    const sensitivity = (document.getElementById('sensitivitySlider')?.value || 50) / 100;
    const res = await fetch(API_BASE + '/api/v1/analyze', {
      method: 'POST',
      headers,
      body: JSON.stringify({ text, sensitivity })
    });
    if (!res.ok) throw new Error('API error ' + res.status);
    data = await res.json();
  } catch (e) {
    btn.textContent = 'Analyze Article';
    btn.disabled = false;
    showToast('Analysis failed: ' + e.message + '. Please try again.');
    return;
  }

  btn.textContent = 'Analyze Article';
  btn.disabled = false;
  renderResults(data);
}

function renderResults(data) {
  const results = document.getElementById('analyzeResults');
  results.classList.remove('hidden');
  results.scrollIntoView({ behavior: 'smooth', block: 'start' });

  const isReal = data.prediction === 'REAL';
  const conf = data.confidence.toFixed(0);
  const tier = data.confidence_tier || (isReal ? 'LIKELY REAL' : 'LIKELY FAKE');

  // Verdict
  const banner = document.getElementById('verdictBanner');
  banner.className = 'verdict-banner ' + (isReal ? 'real' : 'fake');
  document.getElementById('verdictIcon').textContent = isReal ? '✅' : '❌';
  document.getElementById('verdictText').textContent = tier.toUpperCase();
  document.getElementById('verdictText').style.color = isReal ? 'var(--accent)' : 'var(--danger)';

  // Show input quality context
  let subText = 'Analyzed by a 5-model ML ensemble trained on 59,000+ articles.';
  if (data.input_quality === 'short_claim') {
    subText = '⚠️ Short claim detected — not enough context for high-confidence verification.';
  } else if (data.input_quality === 'headline') {
    subText = 'ℹ️ Headline-length input — confidence may be lower than for full articles.';
  }
  document.getElementById('verdictSub').textContent = subText;
  document.getElementById('verdictScore').textContent = conf + '%';
  document.getElementById('verdictScore').style.color = isReal ? 'var(--accent)' : 'var(--danger)';

  // ── Card 1: ML Model (instant from analyze response) ──
  const mlPct = Math.round(data.real_probability * 100);
  animateRing('ringML', mlPct, 'ringMLText');
  setRingColor('ringML', mlPct);
  document.getElementById('mlDetail').textContent = isReal ? 'High structural consistency.' : 'Structural anomalies detected.';

  // ── Explainability words (3.7) ──
  const explainEl = document.getElementById('explainWords');
  if (explainEl) {
    const fakeWords = data.fake_indicator_words || [];
    const realWords = data.real_indicator_words || [];
    if (fakeWords.length || realWords.length) {
      explainEl.innerHTML =
        (fakeWords.length ? `<div class="explain-group"><span class="explain-label fake-label">🚩 Fake Signals</span> ${fakeWords.map(w => `<span class="word-chip fake-chip">${w}</span>`).join('')}</div>` : '') +
        (realWords.length ? `<div class="explain-group"><span class="explain-label real-label">✅ Real Signals</span> ${realWords.map(w => `<span class="word-chip real-chip">${w}</span>`).join('')}</div>` : '');
    } else {
      explainEl.innerHTML = '<p class="text-muted">Explainability not available for this input.</p>';
    }
  }

  // ── Feedback buttons ──
  const feedbackEl = document.getElementById('feedbackBtns');
  if (feedbackEl) {
    const articleTextVal = document.getElementById('articleText').value.trim();
    feedbackEl.innerHTML = `
      <span style="font-size:.85rem;color:var(--text2)">Was this result correct?</span>
      <button class="btn btn-sm btn-outline" onclick="submitFeedback(${JSON.stringify(articleTextVal)}, '${data.prediction}', 'REAL')">👍 It's Real</button>
      <button class="btn btn-sm btn-outline" onclick="submitFeedback(${JSON.stringify(articleTextVal)}, '${data.prediction}', 'FAKE')">👎 It's Fake</button>
    `;
  }


  // Track scores from all 4 sources for combined verdict
  let geminiScore = null, gnewsScore = null, factCheckScore = null;
  const articleText = document.getElementById('articleText').value.trim();

  function updateCombinedVerdict() {
    // Weight: ML 40%, Gemini 25%, GNews 15%, FactCheck 15%  (if all present)
    let sources = [{ score: data.real_probability, weight: 0.40 }];
    let totalWeight = 0.40;
    if (geminiScore !== null) { sources.push({ score: geminiScore, weight: 0.25 }); totalWeight += 0.25; }
    if (gnewsScore !== null) { sources.push({ score: gnewsScore, weight: 0.15 }); totalWeight += 0.15; }
    if (factCheckScore !== null) { sources.push({ score: factCheckScore, weight: 0.20 }); totalWeight += 0.20; }

    const combined = sources.reduce((sum, s) => sum + s.score * s.weight, 0) / totalWeight;
    const combinedReal = combined > 0.5;
    // Confidence = probability of the predicted class (e.g. 63% fake → 63% confidence)
    const conf = Math.round((combinedReal ? combined : 1 - combined) * 100);

    // Update banner with combined verdict
    const banner = document.getElementById('verdictBanner');
    banner.className = 'verdict-banner ' + (combinedReal ? 'real' : 'fake');
    document.getElementById('verdictIcon').textContent = combinedReal ? '✅' : '❌';
    let tier;
    if (conf >= 90) tier = combinedReal ? 'Verified Real' : 'Confirmed Fake';
    else if (conf >= 75) tier = combinedReal ? 'Likely Real' : 'Likely Fake';
    else if (conf >= 60) tier = combinedReal ? 'Leaning Real' : 'Leaning Fake';
    else if (conf >= 52) tier = combinedReal ? 'Slightly Real' : 'Slightly Fake';
    else tier = combinedReal ? 'Borderline Real' : 'Borderline Fake';
    document.getElementById('verdictText').textContent = tier.toUpperCase();
    document.getElementById('verdictText').style.color = combinedReal ? 'var(--accent)' : 'var(--danger)';
    document.getElementById('verdictScore').textContent = conf + '%';
    document.getElementById('verdictScore').style.color = combinedReal ? 'var(--accent)' : 'var(--danger)';

    const srcCount = 1 + (geminiScore !== null ? 1 : 0) + (gnewsScore !== null ? 1 : 0) + (factCheckScore !== null ? 1 : 0);
    document.getElementById('verdictSub').textContent = `Combined analysis from ${srcCount} source${srcCount > 1 ? 's' : ''}: ML Model${geminiScore !== null ? ' + AI Analysis' : ''}${gnewsScore !== null ? ' + GNews' : ''}${factCheckScore !== null ? ' + Fact Check' : ''}`;
  }

  // Initial verdict from ML only
  updateCombinedVerdict();

  // ── Cards 2 & 3: RAG-powered Smart Verify (GNews → Groq in one call) ──
  document.getElementById('geminiDetail').textContent = 'Searching live news...';
  document.getElementById('webDetail').textContent = 'Waiting for AI...';
  animateRing('ringGemini', 0, 'ringGeminiText');
  animateRing('ringWeb', 0, 'ringWebText');
  document.getElementById('ringGeminiText').textContent = '...';
  document.getElementById('ringWebText').textContent = '...';

  // ── Card 4: Fact Check — initialize ──
  document.getElementById('factCheckDetail').textContent = 'Searching...';
  animateRing('ringFactCheck', 0, 'ringFactCheckText');
  document.getElementById('ringFactCheckText').textContent = '...';
  document.getElementById('factCheckBadge').textContent = 'SEARCHING...';
  document.getElementById('factCheckResults').innerHTML = '<p class="text-muted">Searching fact-check database...</p>';

  const smartController = new AbortController();
  const smartTimeout = setTimeout(() => smartController.abort(), 20000); // 20s (GNews + Groq)

  fetch(API_BASE + '/api/v1/smart-verify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: articleText }),
    signal: smartController.signal
  })
  .then(r => r.ok ? r.json() : Promise.reject(r))
  .then(result => {
    clearTimeout(smartTimeout);

    // ── Update AI Analysis ring (Card 2) ──
    geminiScore = result.credibility_score;
    const geminiPct = Math.round(geminiScore * 100);
    animateRing('ringGemini', geminiPct, 'ringGeminiText');
    setRingColor('ringGemini', geminiPct);
    const verdictMap = { 'LIKELY_TRUE': 'Likely True', 'LIKELY_FALSE': 'Likely False', 'MIXED': 'Mixed signals', 'UNVERIFIABLE': 'Unverifiable' };
    document.getElementById('geminiDetail').textContent = verdictMap[result.verdict] || result.verdict;
    const modeLabel = result.mode === 'rag' ? 'AI + LIVE NEWS' : 'AI ANALYSIS';
    document.getElementById('geminiBadge').textContent = modeLabel;
    document.getElementById('geminiAnalysisText').textContent = result.analysis || 'No additional analysis.';

    // ── Update Web Sources ring (Card 3) ──
    const web = result.web || {};
    gnewsScore = web.web_score || 0.3;
    const webPct = Math.round(gnewsScore * 100);
    animateRing('ringWeb', webPct, 'ringWebText');
    setRingColor('ringWeb', webPct);
    const detail = (web.trusted_count || 0) > 0
      ? `${web.trusted_count} trusted source${web.trusted_count > 1 ? 's' : ''} found (${web.total_articles} total)`
      : (web.total_articles || 0) > 0
        ? `${web.total_articles} article${web.total_articles > 1 ? 's' : ''} found, no trusted sources`
        : 'No matching articles found';
    document.getElementById('webDetail').textContent = detail;

    // Show sources in Web Sources section
    const sourcesList = document.getElementById('webSourcesList');
    if (web.articles && web.articles.length > 0) {
      sourcesList.innerHTML = web.articles.map(a =>
        `<div class="source-item"><div class="source-item-info"><a href="${a.url}" target="_blank" class="source-item-name">${a.source}</a><span class="source-item-date">${a.title}</span></div></div>`
      ).join('');
    } else {
      sourcesList.innerHTML = '<p class="text-muted">No matching news articles found.</p>';
    }

    updateCombinedVerdict();
  })
  .catch(err => {
    clearTimeout(smartTimeout);
    // Fallback: try old endpoints separately
    if (err.name === 'AbortError') {
      document.getElementById('geminiDetail').textContent = 'Verification timed out';
      document.getElementById('webDetail').textContent = 'Search timed out';
    } else {
      document.getElementById('geminiDetail').textContent = 'AI Analysis unavailable';
      document.getElementById('webDetail').textContent = 'Web search unavailable';
    }
    document.getElementById('ringGeminiText').textContent = '—';
    document.getElementById('ringWebText').textContent = '—';
    document.getElementById('geminiBadge').textContent = 'UNAVAILABLE';
    document.getElementById('webSourcesList').innerHTML = '<p class="text-muted">Verification service unavailable.</p>';
  });

  // ── Card 4: Google Fact Check API (runs in parallel with smart-verify) ──
  const fcController = new AbortController();
  const fcTimeout = setTimeout(() => fcController.abort(), 15000);

  fetch(API_BASE + '/api/v1/fact-check', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: articleText }),
    signal: fcController.signal
  })
  .then(r => r.ok ? r.json() : Promise.reject(r))
  .then(fc => {
    clearTimeout(fcTimeout);

    if (fc.available && fc.found && fc.reviews && fc.reviews.length > 0) {
      // Update ring
      factCheckScore = fc.factcheck_score;
      const fcPct = Math.round(factCheckScore * 100);
      animateRing('ringFactCheck', fcPct, 'ringFactCheckText');
      setRingColor('ringFactCheck', fcPct);
      document.getElementById('factCheckDetail').textContent =
        `${fc.reviews.length} fact-check${fc.reviews.length > 1 ? 's' : ''} found`;
      document.getElementById('factCheckBadge').textContent = `${fc.total_claims} CLAIM${fc.total_claims > 1 ? 'S' : ''} FOUND`;

      // Render fact-check review cards
      const resultsEl = document.getElementById('factCheckResults');
      resultsEl.innerHTML = fc.reviews.map(r => {
        const ratingLower = (r.rating || '').toLowerCase();
        let ratingClass = 'unknown';
        if (['false','fake','pants on fire','misleading','mostly false','incorrect','wrong','hoax','scam','not true'].some(w => ratingLower.includes(w))) ratingClass = 'false';
        else if (['true','correct','accurate','mostly true','verified','confirmed','real'].some(w => ratingLower.includes(w))) ratingClass = 'true';
        else if (['half true','mixture','partly','partially','needs context','missing context','exaggerated'].some(w => ratingLower.includes(w))) ratingClass = 'mixed';

        return `<div class="factcheck-item">
          <div class="factcheck-header">
            <span class="factcheck-publisher">${r.publisher}</span>
            <span class="factcheck-rating ${ratingClass}">${r.rating}</span>
          </div>
          <p class="factcheck-claim">"${r.claim}"</p>
          ${r.url ? `<a href="${r.url}" target="_blank" rel="noopener" class="factcheck-link">Read full fact-check →</a>` : ''}
          ${r.date ? `<span style="font-size:.72rem;color:var(--text3);margin-left:8px">${r.date}</span>` : ''}
        </div>`;
      }).join('');

      updateCombinedVerdict();
    } else if (fc.available && !fc.found) {
      // API worked but no matching fact-checks found
      animateRing('ringFactCheck', 50, 'ringFactCheckText');
      setRingColor('ringFactCheck', 50);
      document.getElementById('factCheckDetail').textContent = 'No existing fact-checks found';
      document.getElementById('factCheckBadge').textContent = 'NO MATCHES';
      document.getElementById('factCheckResults').innerHTML =
        '<div class="factcheck-empty">✅ No existing fact-checks found for this claim in 200+ databases.<br><small style="color:var(--text3)">This does not mean the claim is true — it may simply not have been fact-checked yet.</small></div>';
    } else {
      // API not configured or failed
      document.getElementById('factCheckDetail').textContent = 'Not configured';
      document.getElementById('factCheckBadge').textContent = 'UNAVAILABLE';
      document.getElementById('ringFactCheckText').textContent = '—';
      document.getElementById('factCheckResults').innerHTML =
        '<p class="text-muted">Fact Check API not configured. Add GOOGLE_FACTCHECK_API_KEY to enable.</p>';
    }
  })
  .catch(err => {
    clearTimeout(fcTimeout);
    document.getElementById('factCheckDetail').textContent = err.name === 'AbortError' ? 'Timed out' : 'Unavailable';
    document.getElementById('factCheckBadge').textContent = 'UNAVAILABLE';
    document.getElementById('ringFactCheckText').textContent = '—';
    document.getElementById('factCheckResults').innerHTML =
      '<p class="text-muted">Fact-check search could not be completed.</p>';
  });
}

function animateRing(ringId, pct, textId) {
  const ring = document.getElementById(ringId);
  const text = document.getElementById(textId);
  let current = 0;
  const step = () => {
    if (current >= pct) {
      ring.style.setProperty('--pct', pct);
      text.textContent = pct + '%';
      return;
    }
    current += 2;
    ring.style.setProperty('--pct', Math.min(current, pct));
    text.textContent = Math.min(current, pct) + '%';
    requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

function setRingColor(ringId, pct) {
  const ring = document.getElementById(ringId);
  if (pct >= 70) ring.style.stroke = 'var(--accent)';
  else if (pct >= 50) ring.style.stroke = 'var(--warning)';
  else ring.style.stroke = 'var(--danger)';
}

// ===== BATCH =====
function setupBatch() {
  const fileInput = document.getElementById('csvFile');
  if (!fileInput) return;
  fileInput.addEventListener('change', e => handleFiles(e.target.files));
  document.getElementById('startBatch')?.addEventListener('click', runBatch);
  document.getElementById('downloadBatch')?.addEventListener('click', downloadBatchCSV);
}

let batchData = [];
function handleFiles(files) {
  if (!files.length) return;
  const file = files[0];
  if (!file.name.endsWith('.csv')) { showToast('Please upload a CSV file'); return; }
  document.getElementById('batchFileName').textContent = `📄 ${file.name} — ready to process`;
  document.getElementById('batchFileInfo').classList.remove('hidden');

  const reader = new FileReader();
  reader.onload = (e) => {
    const rows = e.target.result.split('\n');
    const header = rows[0].split(',').map(h => h.trim().toLowerCase().replace(/"/g, ''));
    const textIdx = header.findIndex(h => h === 'text' || h === 'content');
    if (textIdx === -1) { showToast('CSV must have a "text" or "content" column'); return; }
    batchData = rows.slice(1).filter(r => r.trim()).map(r => {
      const cols = r.split(',');
      return cols.slice(textIdx).join(',').replace(/^"|"$/g, '').trim();
    }).filter(t => t.length >= 50);
    document.getElementById('batchFileName').textContent += ` (${batchData.length} valid rows)`;
  };
  reader.readAsText(file);
}

let batchResults = [];
async function runBatch() {
  if (!batchData.length) { showToast('No valid data found'); return; }
  document.getElementById('batchProgress').classList.remove('hidden');
  batchResults = [];
  const tbody = document.querySelector('#batchTable tbody');
  tbody.innerHTML = '';

  // Build batch request payload
  const articles = batchData.map((text, i) => ({ id: String(i + 1), text }));

  // Process in chunks of 50 (API limit)
  const CHUNK_SIZE = 50;
  let processed = 0;

  for (let start = 0; start < articles.length; start += CHUNK_SIZE) {
    const chunk = articles.slice(start, start + CHUNK_SIZE);
    const pct = Math.round(((start + chunk.length) / articles.length) * 100);
    document.getElementById('batchProgressFill').style.width = pct + '%';
    document.getElementById('batchProgressText').textContent = `Processing ${start + 1}–${start + chunk.length} of ${articles.length}...`;

    try {
      const headers = { 'Content-Type': 'application/json' };
      const token = getToken();
      if (token) headers['Authorization'] = 'Bearer ' + token;

      const res = await fetch(API_BASE + '/api/v1/batch', {
        method: 'POST',
        headers,
        body: JSON.stringify({ articles: chunk })
      });

      if (!res.ok) throw new Error('Batch API error: ' + res.status);
      const batchResponse = await res.json();

      for (const r of batchResponse.results) {
        const idx = parseInt(r.id) - 1;
        const row = {
          preview: (batchData[idx] || '').substring(0, 80) + '...',
          prediction: r.prediction || 'ERROR',
          confidence: r.error ? 'N/A' : (r.confidence || 0).toFixed(1) + '%',
          real_prob: r.error ? 'N/A' : (r.real_probability || 0).toFixed(3),
          fake_prob: r.error ? 'N/A' : (r.fake_probability || 0).toFixed(3),
          red_flags: r.error ? r.error : (r.red_flag_score || 0).toFixed(2)
        };
        batchResults.push(row);
      }
    } catch (e) {
      showToast('Batch error: ' + e.message);
      // Mark remaining in this chunk as errors
      for (const a of chunk) {
        batchResults.push({
          preview: a.text.substring(0, 80) + '...',
          prediction: 'ERROR',
          confidence: 'N/A',
          real_prob: 'N/A',
          fake_prob: 'N/A',
          red_flags: e.message
        });
      }
    }
  }

  document.getElementById('batchProgress').classList.add('hidden');
  document.getElementById('batchResults').classList.remove('hidden');

  batchResults.forEach(r => {
    const tr = document.createElement('tr');
    const predClass = r.prediction === 'REAL' ? 'real' : 'fake';
    tr.innerHTML = `<td>${r.preview}</td><td><span class="pred-pill ${predClass}">${r.prediction}</span></td><td>${r.confidence}</td><td>${r.real_prob}</td><td>${r.fake_prob}</td><td>${r.red_flags}</td>`;
    tbody.appendChild(tr);
  });

  const fakeCount = batchResults.filter(r => r.prediction === 'FAKE').length;
  showToast(`Done: ${batchResults.length} processed — ${fakeCount} FAKE, ${batchResults.length - fakeCount} REAL`);
}

function downloadBatchCSV() {
  if (!batchResults.length) return;
  const header = 'Preview,Prediction,Confidence,Real Prob,Fake Prob,Red Flags\n';
  const csv = header + batchResults.map(r => `"${r.preview}",${r.prediction},${r.confidence},${r.real_prob},${r.fake_prob},${r.red_flags}`).join('\n');
  downloadFile(csv, 'batch_results.csv', 'text/csv');
}

function downloadFile(content, filename, type) {
  const blob = new Blob([content], { type });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
}

// ===== DASHBOARD =====
let chartsInit = false;
let predChart, topicsChart, trendChart;
let dashboardStats = null; // Store for export

async function initDashboard() {
  const token = getToken();
  if (!token) return;

  try {
    const res = await fetch(API_BASE + '/api/v1/user/stats', {
      headers: { 'Authorization': 'Bearer ' + token }
    });
    if (!res.ok) throw new Error('Failed to load stats: ' + res.status);
    const stats = await res.json();
    dashboardStats = stats; // Store for export

    // Update stat cards with per-user data
    document.getElementById('statTotal').textContent = (stats.total || 0).toLocaleString();
    document.getElementById('statConfidence').textContent = stats.avg_confidence || 0;
    document.getElementById('statFake').textContent = (stats.fake_count || 0).toLocaleString();

    const chartColors = {
      green: '#4ADE80', red: '#EF4444', gray: '#64748B',
      blue: '#3B82F6', teal: '#14B8A6', yellow: '#F59E0B'
    };

    // Destroy old charts if re-visiting
    if (predChart) predChart.destroy();
    if (topicsChart) topicsChart.destroy();
    if (trendChart) trendChart.destroy();

    // Prediction Distribution (doughnut) — show gray placeholder if no data
    const hasData = (stats.real_count || 0) + (stats.fake_count || 0) > 0;
    predChart = new Chart(document.getElementById('chartPrediction'), {
      type: 'doughnut',
      data: {
        labels: hasData ? ['Real', 'Fake'] : ['No data yet'],
        datasets: [{
          data: hasData ? [stats.real_count, stats.fake_count] : [1],
          backgroundColor: hasData ? [chartColors.green, chartColors.red] : ['#1F2937'],
          borderWidth: 0
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { position: 'right', labels: { color: '#94A3B8', padding: 16 } },
          tooltip: { enabled: hasData }
        },
        cutout: '65%'
      }
    });

    // Topic Breakdown as bar chart
    topicsChart = new Chart(document.getElementById('chartTopics'), {
      type: 'bar',
      data: {
        labels: ['Total Real', 'Total Fake', 'Avg Confidence'],
        datasets: [{ data: [stats.real_count || 0, stats.fake_count || 0, stats.avg_confidence || 0], backgroundColor: [chartColors.green, chartColors.red, chartColors.teal], borderRadius: 4, barThickness: 20 }]
      },
      options: {
        indexAxis: 'y', responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: '#1F2937' }, ticks: { color: '#94A3B8' } },
          y: { grid: { display: false }, ticks: { color: '#94A3B8' } }
        }
      }
    });

    // Trend line (last 7 days) — fill in missing days
    const today = new Date();
    const last7 = [];
    for (let i = 6; i >= 0; i--) {
      const d = new Date(today);
      d.setDate(d.getDate() - i);
      last7.push(d.toISOString().split('T')[0]);
    }
    const trend = stats.trend || {};
    const realData = last7.map(d => (trend[d] && trend[d].real) || 0);
    const fakeData = last7.map(d => (trend[d] && trend[d].fake) || 0);
    const labels = last7.map(d => {
      const dt = new Date(d + 'T00:00:00');
      return dt.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
    });

    trendChart = new Chart(document.getElementById('chartTrend'), {
      type: 'line',
      data: {
        labels,
        datasets: [
          { label: 'Real', data: realData, borderColor: chartColors.green, backgroundColor: 'rgba(74,222,128,0.1)', fill: true, tension: 0.4, pointRadius: 4 },
          { label: 'Fake', data: fakeData, borderColor: chartColors.red, backgroundColor: 'rgba(239,68,68,0.1)', fill: true, tension: 0.4, pointRadius: 4 }
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { labels: { color: '#94A3B8' } } },
        scales: {
          x: { grid: { color: '#1F2937' }, ticks: { color: '#94A3B8' } },
          y: { grid: { color: '#1F2937' }, ticks: { color: '#94A3B8', stepSize: 1 }, beginAtZero: true }
        }
      }
    });

    // Recent analyses table
    const tbody = document.getElementById('recentBody');
    tbody.innerHTML = '';
    if (!stats.recent || stats.recent.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text3);padding:24px">No analyses yet. Go to Analyze to get started!</td></tr>';
    } else {
      stats.recent.forEach(r => {
        const cls = r.prediction === 'REAL' ? 'real' : 'fake';
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${new Date(r.date).toLocaleString()}</td><td><span class="pred-pill ${cls}">${r.prediction}</span></td><td>${r.confidence}%</td><td><span class="cat-pill">${r.red_flags}%</span></td><td>${r.preview.substring(0, 80)}...</td>`;
        tbody.appendChild(tr);
      });
    }

  } catch (e) {
    console.error('Dashboard load failed:', e);
    document.getElementById('statTotal').textContent = '0';
    document.getElementById('statConfidence').textContent = '0';
    document.getElementById('statFake').textContent = '0';
  }
}

// ===== HISTORY =====
let historyPage = 1;

async function loadHistory() {
  const tbody = document.getElementById('historyBody');
  if (!tbody) return;
  const token = getToken();
  if (!token) return;

  const activeFilter = document.querySelector('.filter-pills .pill.active')?.dataset.filter || 'all';
  const limit = parseInt(document.getElementById('historyPageSize')?.value) || 25;

  try {
    const res = await fetch(
      `${API_BASE}/api/v1/user/history?page=${historyPage}&limit=${limit}&filter=${activeFilter}`,
      { headers: { 'Authorization': 'Bearer ' + token } }
    );
    if (!res.ok) throw new Error('Failed to load history');
    const data = await res.json();

    tbody.innerHTML = '';
    if (data.items.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text3);padding:24px">No analyses found. Start analyzing articles!</td></tr>';
    } else {
      data.items.forEach(r => {
        const cls = r.prediction === 'REAL' ? 'real' : 'fake';
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${new Date(r.date).toLocaleString()}</td><td><span class="pred-pill ${cls}">● ${r.prediction}</span></td><td>${r.confidence}%</td><td>${r.real_prob}</td><td>${r.red_flags}%</td><td>${r.preview.substring(0, 80)}...</td>`;
        tbody.appendChild(tr);
      });
    }

    const start = (data.page - 1) * data.limit + 1;
    const end = Math.min(data.page * data.limit, data.total);
    document.getElementById('historyPagInfo').textContent = data.total > 0 ? `${start}-${end} of ${data.total}` : '0 results';

    // Pagination button handlers
    document.getElementById('historyPrev').onclick = () => { if (historyPage > 1) { historyPage--; loadHistory(); } };
    document.getElementById('historyNext').onclick = () => { if (historyPage < data.pages) { historyPage++; loadHistory(); } };

  } catch (e) {
    console.warn('History load failed:', e.message);
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text3)">Failed to load history</td></tr>';
  }
}

// ===== EXPORT REPORT =====
// Global store for the last analysis data (populated by renderResults)
let lastAnalysisData = null;
let lastAnalysisText = '';
let lastGeminiAnalysis = '';
let lastWebSources = [];

// Helper: get current displayed values from DOM
function _getReportData() {
  return {
    verdict: document.getElementById('verdictText')?.textContent || 'N/A',
    confidence: document.getElementById('verdictScore')?.textContent || 'N/A',
    verdictSub: document.getElementById('verdictSub')?.textContent || '',
    mlScore: document.getElementById('ringMLText')?.textContent || 'N/A',
    mlDetail: document.getElementById('mlDetail')?.textContent || '',
    aiScore: document.getElementById('ringGeminiText')?.textContent || 'N/A',
    aiDetail: document.getElementById('geminiDetail')?.textContent || '',
    aiBadge: document.getElementById('geminiBadge')?.textContent || '',
    aiAnalysis: document.getElementById('geminiAnalysisText')?.textContent || '',
    webScore: document.getElementById('ringWebText')?.textContent || 'N/A',
    webDetail: document.getElementById('webDetail')?.textContent || '',
    articleText: document.getElementById('articleText')?.value?.trim() || '',
    timestamp: new Date().toLocaleString(),
    userName: currentUser?.name || 'Anonymous',
  };
}

function exportReportPDF() {
  const d = _getReportData();
  if (!d.articleText) { showToast('No analysis to export.'); return; }

  const isReal = d.verdict.toLowerCase().includes('real');
  const verdictColor = isReal ? '#22C55E' : '#EF4444';
  const verdictBg = isReal ? 'rgba(34,197,94,.08)' : 'rgba(239,68,68,.08)';
  const verdictIcon = isReal ? '✅' : '❌';
  const preview = d.articleText.length > 500 ? d.articleText.substring(0, 500) + '...' : d.articleText;

  const html = `<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<title>Verify — Analysis Report</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{font-family:'Inter',system-ui,sans-serif;color:#1a1a2e;background:#fff;padding:48px 56px;max-width:800px;margin:0 auto;line-height:1.7}
  .header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:36px;padding-bottom:20px;border-bottom:2px solid #e2e8f0}
  .logo{display:flex;align-items:center;gap:10px}
  .logo svg{width:32px;height:32px}
  .logo span{font-size:1.5rem;font-weight:800;letter-spacing:-.5px}
  .meta{text-align:right;color:#64748b;font-size:.82rem;line-height:1.8}
  .verdict-box{background:${verdictBg};border:2px solid ${verdictColor}22;border-radius:16px;padding:24px 28px;display:flex;justify-content:space-between;align-items:center;margin-bottom:28px}
  .verdict-left{display:flex;align-items:center;gap:14px}
  .verdict-icon{font-size:2.2rem}
  .verdict-label{font-size:1.4rem;font-weight:800;color:${verdictColor};text-transform:uppercase;letter-spacing:.5px}
  .verdict-sub{font-size:.82rem;color:#64748b;margin-top:2px}
  .verdict-score{font-size:2.4rem;font-weight:800;color:${verdictColor}}
  .verdict-score-label{font-size:.7rem;color:#64748b;text-transform:uppercase;letter-spacing:.5px;display:block;text-align:center}
  h2{font-size:1.1rem;font-weight:700;color:#1B3A4B;margin:28px 0 12px;padding-bottom:6px;border-bottom:1px solid #e2e8f0}
  .scores-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;margin-bottom:8px}
  .score-card{background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:18px;text-align:center}
  .score-card .label{font-size:.75rem;color:#64748b;text-transform:uppercase;font-weight:600;letter-spacing:.5px}
  .score-card .value{font-size:1.8rem;font-weight:800;color:#1B3A4B;margin:6px 0 4px}
  .score-card .detail{font-size:.78rem;color:#64748b}
  .article-preview{background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:18px;font-size:.85rem;color:#475569;white-space:pre-wrap;word-break:break-word;max-height:300px;overflow:hidden}
  .ai-analysis{background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;padding:18px;font-size:.88rem;color:#166534;font-style:italic;line-height:1.7}
  .footer{margin-top:40px;padding-top:16px;border-top:1px solid #e2e8f0;text-align:center;color:#94a3b8;font-size:.75rem}
  .web-detail{background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:14px 18px;font-size:.85rem;color:#475569}
  @media print{body{padding:24px 32px}
    .verdict-box{break-inside:avoid}}
</style>
</head><body>

<div class="header">
  <div class="logo">
    <svg viewBox="0 0 36 36" fill="none">
      <path d="M6 20L15 30L32 6" stroke="#1B3A4B" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M12 20L15 26L32 5" stroke="#4ADE80" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    <span>Verify</span>
  </div>
  <div class="meta">
    <div><strong>Analysis Report</strong></div>
    <div>${d.timestamp}</div>
    <div>Analyst: ${d.userName}</div>
  </div>
</div>

<div class="verdict-box">
  <div class="verdict-left">
    <span class="verdict-icon">${verdictIcon}</span>
    <div>
      <div class="verdict-label">${d.verdict}</div>
      <div class="verdict-sub">${d.verdictSub}</div>
    </div>
  </div>
  <div style="text-align:center">
    <div class="verdict-score">${d.confidence}</div>
    <span class="verdict-score-label">Confidence</span>
  </div>
</div>

<h2>📊 Source Scores</h2>
<div class="scores-grid">
  <div class="score-card">
    <div class="label">🧠 ML Model</div>
    <div class="value">${d.mlScore}</div>
    <div class="detail">${d.mlDetail}</div>
  </div>
  <div class="score-card">
    <div class="label">✨ AI Analysis</div>
    <div class="value">${d.aiScore}</div>
    <div class="detail">${d.aiDetail}</div>
  </div>
  <div class="score-card">
    <div class="label">🌐 GNews API</div>
    <div class="value">${d.webScore}</div>
    <div class="detail">${d.webDetail}</div>
  </div>
</div>

${d.aiAnalysis && d.aiAnalysis !== 'Analysis will appear here after processing.' ? `
<h2>✨ AI Analysis Detail</h2>
<div class="ai-analysis">${d.aiAnalysis}</div>
` : ''}

<h2>📰 Analyzed Article</h2>
<div class="article-preview">${preview}</div>

<div class="footer">
  <p>Generated by <strong>Verify</strong> — AI-Powered News Verification Platform</p>
  <p>This report is auto-generated. Cross-check critical claims with multiple sources.</p>
</div>

</body></html>`;

  const printWindow = window.open('', '_blank', 'width=900,height=700');
  printWindow.document.write(html);
  printWindow.document.close();
  // Trigger print after fonts load
  printWindow.onload = () => {
    setTimeout(() => printWindow.print(), 400);
  };
  showToast('PDF report opened — use Save as PDF in the print dialog.');
}

function exportReportText() {
  const d = _getReportData();
  if (!d.articleText) { showToast('No analysis to export.'); return; }

  const divider = '═'.repeat(60);
  const thinDiv = '─'.repeat(60);
  const preview = d.articleText.length > 800 ? d.articleText.substring(0, 800) + '...' : d.articleText;

  const report = `${divider}
  VERIFY — AI-Powered News Verification Report
${divider}

Date:     ${d.timestamp}
Analyst:  ${d.userName}

${thinDiv}
  VERDICT
${thinDiv}

  Result:     ${d.verdict}
  Confidence: ${d.confidence}
  Summary:    ${d.verdictSub}

${thinDiv}
  SOURCE SCORES
${thinDiv}

  🧠 ML Model:     ${d.mlScore}  —  ${d.mlDetail}
  ✨ AI Analysis:   ${d.aiScore}  —  ${d.aiDetail}
  🌐 GNews API:     ${d.webScore}  —  ${d.webDetail}

${d.aiAnalysis && d.aiAnalysis !== 'Analysis will appear here after processing.' ? `${thinDiv}
  AI ANALYSIS DETAIL
${thinDiv}

${d.aiAnalysis}
` : ''}
${thinDiv}
  ANALYZED ARTICLE
${thinDiv}

${preview}

${divider}
Generated by Verify — AI-Powered News Verification Platform
This report is auto-generated. Cross-check critical claims with multiple sources.
${divider}
`;

  downloadFile(report, `verify_report_${Date.now()}.txt`, 'text/plain');
  showToast('Text report downloaded!');
}

// ===== DASHBOARD EXPORT =====
document.getElementById('exportDashboard')?.addEventListener('click', () => {
  if (!dashboardStats) { showToast('No dashboard data to export. Visit the dashboard first.'); return; }
  const s = dashboardStats;
  const timestamp = new Date().toLocaleString();

  // Build CSV with summary + recent analyses
  let csv = `Verify Dashboard Export — ${timestamp}\n\n`;
  csv += `Metric,Value\n`;
  csv += `Total Analyzed,${s.total || 0}\n`;
  csv += `Real Count,${s.real_count || 0}\n`;
  csv += `Fake Count,${s.fake_count || 0}\n`;
  csv += `Avg Confidence,${s.avg_confidence || 0}%\n`;
  csv += `Global Total,${s.global_total || 0}\n`;
  csv += `Global Fake Count,${s.global_fake_count || 0}\n\n`;

  // Trend data
  if (s.trend && Object.keys(s.trend).length > 0) {
    csv += `\nDaily Trend\nDate,Real,Fake\n`;
    Object.keys(s.trend).sort().forEach(day => {
      csv += `${day},${s.trend[day].real || 0},${s.trend[day].fake || 0}\n`;
    });
  }

  // Recent analyses
  if (s.recent && s.recent.length > 0) {
    csv += `\nRecent Analyses\nDate,Prediction,Confidence,Red Flag Score,Preview\n`;
    s.recent.forEach(r => {
      const preview = (r.preview || '').replace(/"/g, '""');
      csv += `${r.date},${r.prediction},${r.confidence}%,${r.red_flags}%,"${preview}"\n`;
    });
  }

  downloadFile(csv, `verify_dashboard_${Date.now()}.csv`, 'text/csv');
  showToast('Dashboard data exported!');
});

// ===== HISTORY EXPORT =====
document.getElementById('exportHistory')?.addEventListener('click', async () => {
  const token = getToken();
  if (!token) { showToast('Please sign in to export history.'); return; }

  const formatEl = document.getElementById('exportFormat');
  const isJSON = formatEl && formatEl.value.includes('JSON');
  const activeFilter = document.querySelector('.filter-pills .pill.active')?.dataset.filter || 'all';

  showToast('Fetching history for export...');
  try {
    const res = await fetch(
      `${API_BASE}/api/v1/user/history?page=1&limit=1000&filter=${activeFilter}`,
      { headers: { 'Authorization': 'Bearer ' + token } }
    );
    if (!res.ok) throw new Error('Failed to fetch history');
    const data = await res.json();

    if (!data.items || data.items.length === 0) {
      showToast('No history data to export.');
      return;
    }

    if (isJSON) {
      const json = JSON.stringify(data.items, null, 2);
      downloadFile(json, `verify_history_${Date.now()}.json`, 'application/json');
    } else {
      let csv = 'Date,Prediction,Confidence,Real Probability,Red Flag Score,Preview\n';
      data.items.forEach(r => {
        const preview = (r.preview || '').replace(/"/g, '""');
        csv += `${r.date},${r.prediction},${r.confidence}%,${r.real_prob || ''},${r.red_flags}%,"${preview}"\n`;
      });
      downloadFile(csv, `verify_history_${Date.now()}.csv`, 'text/csv');
    }

    showToast(`Exported ${data.items.length} records!`);
  } catch (e) {
    showToast('Export failed: ' + e.message);
  }
});
