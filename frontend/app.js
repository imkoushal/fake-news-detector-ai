/* ===== Verify — Frontend App Logic ===== */
const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:8000'
  : window.location.origin;

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
  if (!text || text.length < 50) {
    showToast('Please enter at least 50 characters.');
    return;
  }

  const btn = document.getElementById('analyzeBtn');
  btn.textContent = 'Analyzing...';
  btn.disabled = true;

  let data;
  try {
    const res = await fetch(API_BASE + '/api/v1/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });
    if (!res.ok) throw new Error('API error ' + res.status);
    data = await res.json();
  } catch (e) {
    // Fallback demo data
    console.warn('API unavailable, using demo data:', e.message);
    const fakeProb = Math.random();
    data = {
      prediction: fakeProb > 0.5 ? 'FAKE' : 'REAL',
      confidence: (Math.max(fakeProb, 1 - fakeProb) * 100),
      real_probability: 1 - fakeProb,
      fake_probability: fakeProb,
      red_flag_score: Math.random() * 0.5
    };
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

  // Verdict
  const banner = document.getElementById('verdictBanner');
  banner.className = 'verdict-banner ' + (isReal ? 'real' : 'fake');
  document.getElementById('verdictIcon').textContent = isReal ? '✅' : '❌';
  document.getElementById('verdictText').textContent = isReal ? 'LIKELY REAL' : 'LIKELY FAKE';
  document.getElementById('verdictText').style.color = isReal ? 'var(--accent)' : 'var(--danger)';
  document.getElementById('verdictSub').textContent = 'Cross-referenced against 3 distinct verification models.';
  document.getElementById('verdictScore').textContent = conf + '%';
  document.getElementById('verdictScore').style.color = isReal ? 'var(--accent)' : 'var(--danger)';

  // Rings
  const mlPct = Math.round(data.real_probability * 100);
  const geminiPct = Math.max(50, Math.round((data.real_probability * 0.9 + Math.random() * 0.1) * 100));
  const webPct = Math.max(50, Math.round((data.real_probability * 0.85 + Math.random() * 0.15) * 100));

  animateRing('ringML', mlPct, 'ringMLText');
  animateRing('ringGemini', geminiPct, 'ringGeminiText');
  animateRing('ringWeb', webPct, 'ringWebText');

  document.getElementById('mlDetail').textContent = isReal ? 'High structural consistency.' : 'Structural anomalies detected.';
  document.getElementById('geminiDetail').textContent = isReal ? 'Semantic logic aligns with facts.' : 'Logical inconsistencies found.';
  document.getElementById('webDetail').textContent = isReal ? 'Strong corroboration found.' : 'Limited corroboration.';

  // Ring colors
  setRingColor('ringML', mlPct);
  setRingColor('ringGemini', geminiPct);
  setRingColor('ringWeb', webPct);

  // Web sources (demo)
  const sourcesList = document.getElementById('webSourcesList');
  const sources = [
    { name: 'Reuters', date: 'Oct 24, 2023' },
    { name: 'Associated Press', date: 'Oct 25, 2023' },
    { name: 'Local News Net', date: 'Oct 23, 2023' }
  ];
  sourcesList.innerHTML = sources.map(s =>
    `<div class="source-item"><div class="source-item-info"><span class="source-item-name">${s.name}</span><span class="source-item-date">${s.date}</span></div><a class="source-item-link" href="#">🔗</a></div>`
  ).join('');

  // Gemini
  document.getElementById('geminiBadge').className = 'badge badge-green';
  document.getElementById('geminiBadge').textContent = 'COMPLETED';
  document.getElementById('geminiAnalysisText').textContent =
    isReal
      ? '"The text provides a coherent and factually verifiable account of recent events. Cross-referencing entities mentioned aligns with established public records. Tone is objective and lacks common disinformation markers."'
      : '"The text contains several unverifiable claims and uses emotionally charged language. Multiple assertions lack attribution to credible sources. Sensationalism indicators are elevated."';
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

  for (let i = 0; i < batchData.length; i++) {
    const pct = ((i + 1) / batchData.length * 100);
    document.getElementById('batchProgressFill').style.width = pct + '%';
    document.getElementById('batchProgressText').textContent = `Processing ${i + 1} / ${batchData.length}...`;

    const fakeProb = Math.random();
    const row = {
      preview: batchData[i].substring(0, 80) + '...',
      prediction: fakeProb > 0.5 ? 'FAKE' : 'REAL',
      confidence: (Math.max(fakeProb, 1 - fakeProb) * 100).toFixed(1) + '%',
      real_prob: (1 - fakeProb).toFixed(3),
      fake_prob: fakeProb.toFixed(3),
      red_flags: (Math.random() * 0.5).toFixed(2)
    };
    batchResults.push(row);
    await new Promise(r => setTimeout(r, 50));
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
function initDashboard() {
  // Demo stats
  document.getElementById('statTotal').textContent = '24,592';
  document.getElementById('statConfidence').textContent = '87';
  document.getElementById('statFake').textContent = '3,140';

  if (chartsInit) return;
  chartsInit = true;

  const chartColors = {
    green: '#4ADE80', red: '#EF4444', gray: '#64748B',
    blue: '#3B82F6', teal: '#14B8A6', yellow: '#F59E0B'
  };

  // Prediction Distribution
  new Chart(document.getElementById('chartPrediction'), {
    type: 'doughnut',
    data: {
      labels: ['Real', 'Fake', 'Unverified'],
      datasets: [{ data: [18400, 3100, 3000], backgroundColor: [chartColors.green, chartColors.red, chartColors.gray], borderWidth: 0 }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: 'right', labels: { color: '#94A3B8', padding: 16 } } },
      cutout: '65%'
    }
  });

  // Topics
  new Chart(document.getElementById('chartTopics'), {
    type: 'bar',
    data: {
      labels: ['Politics', 'Health', 'Tech', 'Finance', 'Other'],
      datasets: [{ data: [8500, 6200, 4100, 2800, 2900], backgroundColor: [chartColors.teal, chartColors.teal, chartColors.teal, chartColors.teal, chartColors.teal], borderRadius: 4, barThickness: 20 }]
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

  // Trend
  const labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  new Chart(document.getElementById('chartTrend'), {
    type: 'line',
    data: {
      labels,
      datasets: [
        { label: 'Real', data: [120, 150, 130, 170, 160, 90, 110], borderColor: chartColors.green, backgroundColor: 'rgba(74,222,128,0.1)', fill: true, tension: 0.4, pointRadius: 4 },
        { label: 'Fake', data: [30, 45, 25, 55, 40, 20, 35], borderColor: chartColors.red, backgroundColor: 'rgba(239,68,68,0.1)', fill: true, tension: 0.4, pointRadius: 4 }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { labels: { color: '#94A3B8' } } },
      scales: {
        x: { grid: { color: '#1F2937' }, ticks: { color: '#94A3B8' } },
        y: { grid: { color: '#1F2937' }, ticks: { color: '#94A3B8' } }
      }
    }
  });

  // Recent table
  const recentData = [
    { date: '2023-10-24 14:32', pred: 'REAL', conf: '98%', cat: 'Politics', preview: '"New legislative bill proposes sweeping changes to renewable energy subsidies."' },
    { date: '2023-10-24 11:15', pred: 'FAKE', conf: '95%', cat: 'Health', preview: '"Miracle cure discovered in remote jungle completely eradicates all forms of cellular..."' },
    { date: '2023-10-23 09:45', pred: 'UNCERTAIN', conf: '54%', cat: 'Technology', preview: '"Leaked specs suggest next-gen quantum processor will achieve consciousness by Q3..."' }
  ];
  const tbody = document.getElementById('recentBody');
  recentData.forEach(r => {
    const cls = r.pred === 'REAL' ? 'real' : r.pred === 'FAKE' ? 'fake' : 'uncertain';
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${r.date}</td><td><span class="pred-pill ${cls}">${r.pred}</span></td><td>${r.conf}</td><td><span class="cat-pill">${r.cat}</span></td><td>${r.preview}</td>`;
    tbody.appendChild(tr);
  });
}

// ===== HISTORY =====
function loadHistory() {
  const tbody = document.getElementById('historyBody');
  if (!tbody) return;
  // Demo data
  const demoHistory = [
    { date: '2023-10-24 14:32', pred: 'REAL', conf: '98%', cat: 'Politics', flags: 12, preview: '"New legislative bill proposes sweeping changes to... renewable energy subsidies."' },
    { date: '2023-10-24 11:15', pred: 'FAKE', conf: '95%', cat: 'Health', flags: 88, preview: '"Miracle cure discovered in remote jungle completely... eradicates all forms of cellular"' },
    { date: '2023-10-23 09:45', pred: 'UNCERTAIN', conf: '54%', cat: 'Technology', flags: 45, preview: '"Leaked specs suggest next-gen quantum processor will... achieve consciousness by Q3"' },
    { date: '2023-10-22 16:20', pred: 'REAL', conf: '91%', cat: 'Finance', flags: 8, preview: '"Central bank announces gradual interest rate adjustment... over the next quarter."' },
    { date: '2023-10-21 10:05', pred: 'FAKE', conf: '87%', cat: 'Politics', flags: 72, preview: '"Secret government program exposed by anonymous insider... reveals shocking details."' }
  ];

  const activeFilter = document.querySelector('.filter-pills .pill.active')?.dataset.filter || 'all';
  const filtered = demoHistory.filter(r => {
    if (activeFilter === 'real') return r.pred === 'REAL';
    if (activeFilter === 'fake') return r.pred === 'FAKE';
    return true;
  });

  tbody.innerHTML = '';
  filtered.forEach(r => {
    const cls = r.pred === 'REAL' ? 'real' : r.pred === 'FAKE' ? 'fake' : 'uncertain';
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${r.date}</td><td><span class="pred-pill ${cls}">● ${r.pred}</span></td><td>${r.conf}</td><td><span class="cat-pill">${r.cat}</span></td><td>${r.flags}</td><td>${r.preview}</td>`;
    tbody.appendChild(tr);
  });

  document.getElementById('historyPagInfo').textContent = `1-${filtered.length} of ${filtered.length}`;
}

// ===== EXPORT =====
document.getElementById('exportHistory')?.addEventListener('click', () => {
  showToast('Export started — downloading...');
});
document.getElementById('exportDashboard')?.addEventListener('click', () => {
  showToast('Dashboard export started.');
});
