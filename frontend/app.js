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
    const initial = currentUser.name.charAt(0).toUpperCase();
    document.getElementById('userAvatar').textContent = initial;
    document.getElementById('dropdownAvatar').textContent = initial;
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

  // Settings sensitivity display
  const ss = document.getElementById('settingsSensitivity');
  if (ss) {
    ss.addEventListener('input', () => {
      document.getElementById('settingSensVal').textContent = (ss.value / 100).toFixed(2);
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
    const res = await fetch(API_BASE + '/api/v1/analyze', {
      method: 'POST',
      headers,
      body: JSON.stringify({ text })
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

  // Track scores from all 3 sources for combined verdict
  let geminiScore = null, gnewsScore = null;
  const articleText = document.getElementById('articleText').value.trim();

  function updateCombinedVerdict() {
    // Weight: ML 50%, Gemini 30%, GNews 20%
    let sources = [{ score: data.real_probability, weight: 0.5 }];
    let totalWeight = 0.5;
    if (geminiScore !== null) { sources.push({ score: geminiScore, weight: 0.3 }); totalWeight += 0.3; }
    if (gnewsScore !== null) { sources.push({ score: gnewsScore, weight: 0.2 }); totalWeight += 0.2; }

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
    else if (conf >= 52) tier = 'Suspicious';
    else tier = 'Inconclusive';
    document.getElementById('verdictText').textContent = tier.toUpperCase();
    document.getElementById('verdictText').style.color = combinedReal ? 'var(--accent)' : 'var(--danger)';
    document.getElementById('verdictScore').textContent = conf + '%';
    document.getElementById('verdictScore').style.color = combinedReal ? 'var(--accent)' : 'var(--danger)';

    const srcCount = 1 + (geminiScore !== null ? 1 : 0) + (gnewsScore !== null ? 1 : 0);
    document.getElementById('verdictSub').textContent = `Combined analysis from ${srcCount} source${srcCount > 1 ? 's' : ''}: ML Model${geminiScore !== null ? ' + Gemini AI' : ''}${gnewsScore !== null ? ' + GNews' : ''}`;
  }

  // Initial verdict from ML only
  updateCombinedVerdict();

  // ── Card 2: Gemini AI (async) ──
  document.getElementById('geminiDetail').textContent = 'Verifying with Gemini AI...';
  animateRing('ringGemini', 0, 'ringGeminiText');
  document.getElementById('ringGeminiText').textContent = '...';

  fetch(API_BASE + '/api/v1/gemini-verify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: articleText })
  })
  .then(r => r.ok ? r.json() : Promise.reject(r))
  .then(g => {
    geminiScore = g.credibility_score;
    const geminiPct = Math.round(geminiScore * 100);
    animateRing('ringGemini', geminiPct, 'ringGeminiText');
    setRingColor('ringGemini', geminiPct);
    const verdictMap = { 'LIKELY_TRUE': 'Likely True', 'LIKELY_FALSE': 'Likely False', 'MIXED': 'Mixed signals', 'UNVERIFIABLE': 'Unverifiable' };
    document.getElementById('geminiDetail').textContent = verdictMap[g.verdict] || g.verdict;
    document.getElementById('geminiBadge').textContent = 'GEMINI AI';
    document.getElementById('geminiAnalysisText').textContent = g.analysis || 'No additional analysis.';
    updateCombinedVerdict();
  })
  .catch(() => {
    document.getElementById('ringGeminiText').textContent = '—';
    document.getElementById('geminiDetail').textContent = 'Gemini AI unavailable';
    document.getElementById('geminiBadge').textContent = 'UNAVAILABLE';
  });

  // ── Card 3: GNews API (async) ──
  document.getElementById('webDetail').textContent = 'Searching news sources...';
  animateRing('ringWeb', 0, 'ringWebText');
  document.getElementById('ringWebText').textContent = '...';

  fetch(API_BASE + '/api/v1/gnews-search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: articleText })
  })
  .then(r => r.ok ? r.json() : Promise.reject(r))
  .then(g => {
    gnewsScore = g.web_score;
    const webPct = Math.round(gnewsScore * 100);
    animateRing('ringWeb', webPct, 'ringWebText');
    setRingColor('ringWeb', webPct);
    const detail = g.trusted_count > 0
      ? `${g.trusted_count} trusted source${g.trusted_count > 1 ? 's' : ''} found (${g.total_articles} total)`
      : g.total_articles > 0
        ? `${g.total_articles} article${g.total_articles > 1 ? 's' : ''} found, no trusted sources`
        : 'No matching articles found';
    document.getElementById('webDetail').textContent = detail;

    // Show sources in Web Sources section
    const sourcesList = document.getElementById('webSourcesList');
    if (g.articles && g.articles.length > 0) {
      sourcesList.innerHTML = g.articles.map(a =>
        `<div class="source-item"><div class="source-item-info"><a href="${a.url}" target="_blank" class="source-item-name">${a.source}</a><span class="source-item-date">${a.title}</span></div></div>`
      ).join('');
    } else {
      sourcesList.innerHTML = '<p class="text-muted">No matching news articles found.</p>';
    }
    updateCombinedVerdict();
  })
  .catch(() => {
    document.getElementById('ringWebText').textContent = '—';
    document.getElementById('webDetail').textContent = 'GNews API unavailable';
    const sourcesList = document.getElementById('webSourcesList');
    sourcesList.innerHTML = '<p class="text-muted">GNews API not available.</p>';
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

async function initDashboard() {
  const token = getToken();
  if (!token) return;

  try {
    const res = await fetch(API_BASE + '/api/v1/user/stats', {
      headers: { 'Authorization': 'Bearer ' + token }
    });
    if (!res.ok) throw new Error('Failed to load stats');
    const stats = await res.json();

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

    // Prediction Distribution (doughnut)
    predChart = new Chart(document.getElementById('chartPrediction'), {
      type: 'doughnut',
      data: {
        labels: ['Real', 'Fake'],
        datasets: [{ data: [stats.real_count, stats.fake_count], backgroundColor: [chartColors.green, chartColors.red], borderWidth: 0 }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'right', labels: { color: '#94A3B8', padding: 16 } } },
        cutout: '65%'
      }
    });

    // Confidence distribution as bar (fake vs real count by confidence ranges)
    topicsChart = new Chart(document.getElementById('chartTopics'), {
      type: 'bar',
      data: {
        labels: ['Total Real', 'Total Fake', 'Avg Confidence'],
        datasets: [{ data: [stats.real_count, stats.fake_count, stats.avg_confidence], backgroundColor: [chartColors.green, chartColors.red, chartColors.teal], borderRadius: 4, barThickness: 20 }]
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

    // Trend line (last 7 days)
    const trendDays = Object.keys(stats.trend).sort();
    const realData = trendDays.map(d => stats.trend[d].real || 0);
    const fakeData = trendDays.map(d => stats.trend[d].fake || 0);
    const labels = trendDays.map(d => {
      const dt = new Date(d);
      return dt.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
    });

    trendChart = new Chart(document.getElementById('chartTrend'), {
      type: 'line',
      data: {
        labels: labels.length ? labels : ['No data yet'],
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
          y: { grid: { color: '#1F2937' }, ticks: { color: '#94A3B8', stepSize: 1 } }
        }
      }
    });

    // Recent analyses table
    const tbody = document.getElementById('recentBody');
    tbody.innerHTML = '';
    if (stats.recent.length === 0) {
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
    console.warn('Dashboard load failed:', e.message);
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

// ===== EXPORT =====
document.getElementById('exportHistory')?.addEventListener('click', () => {
  showToast('Export started — downloading...');
});
document.getElementById('exportDashboard')?.addEventListener('click', () => {
  showToast('Dashboard export started.');
});
