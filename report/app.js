/* ===== VERIFY REPORT — FRONTEND LOGIC ===== */

let currentSlide = 0;
const totalSlides = 5;

// ===== ROUTING & SWITCHING =====
function goToSlide(index) {
  if (index < 0 || index >= totalSlides) return;
  
  // Update class active
  document.querySelectorAll('.slide').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
  
  const targetSlide = document.getElementById('slide-' + index);
  if (targetSlide) {
    targetSlide.classList.add('active');
  }
  
  const targetLink = document.querySelector(`[data-slide="${index}"]`);
  if (targetLink) {
    targetLink.classList.add('active');
  }
  
  currentSlide = index;
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function nextSlide() {
  if (currentSlide < totalSlides - 1) {
    goToSlide(currentSlide + 1);
  } else {
    goToSlide(0); // Loop back
  }
}

function prevSlide() {
  if (currentSlide > 0) {
    goToSlide(currentSlide - 1);
  } else {
    goToSlide(totalSlides - 1); // Loop back
  }
}

// ===== KEYBOARD SHORTCUTS =====
document.addEventListener('keydown', (e) => {
  if (e.key === 'ArrowRight' || e.key === 'Space') {
    nextSlide();
  } else if (e.key === 'ArrowLeft') {
    prevSlide();
  }
});

// ===== THEME TOGGLING =====
function initTheme() {
  const toggle = document.getElementById('themeToggle');
  const savedTheme = localStorage.getItem('report_theme') || 'dark';
  
  document.documentElement.setAttribute('data-theme', savedTheme);
  updateThemeIcon(savedTheme);
  
  toggle.addEventListener('click', () => {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('report_theme', next);
    updateThemeIcon(next);
    
    // Redraw charts to update colors
    renderCharts();
  });
}

function updateThemeIcon(theme) {
  const icon = document.querySelector('.theme-icon');
  if (icon) {
    icon.textContent = theme === 'dark' ? '☀️' : '🌙';
  }
}

// ===== CHART.JS RENDERER =====
let trajectoryChart = null;

function renderCharts() {
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  const textColor = isDark ? '#94A3B8' : '#475569';
  const gridColor = isDark ? 'rgba(255, 255, 255, 0.05)' : 'rgba(15, 23, 42, 0.05)';
  
  const ctx = document.getElementById('trajectoryChart');
  if (!ctx) return;
  
  if (trajectoryChart) {
    trajectoryChart.destroy();
  }
  
  const data = {
    labels: [
      'Honest Baseline (LR+RF)', 
      'Linguistic Meta (LR+RF)', 
      'Stacking Ensemble', 
      'Ensemble + RandSearch'
    ],
    datasets: [{
      label: 'Accuracy (%)',
      data: [92.32, 93.35, 94.69, 94.74],
      borderColor: '#0D9488',
      backgroundColor: 'rgba(13, 148, 136, 0.1)',
      borderWidth: 3,
      pointBackgroundColor: '#0D9488',
      pointBorderColor: isDark ? '#0B0F19' : '#FFFFFF',
      pointHoverBackgroundColor: '#FFFFFF',
      pointHoverBorderColor: '#0D9488',
      pointRadius: 6,
      pointHoverRadius: 8,
      fill: true,
      tension: 0.35
    },
    {
      label: 'F1-Score (%)',
      data: [92.05, 93.15, 94.61, 94.66],
      borderColor: '#2563EB',
      backgroundColor: 'rgba(37, 99, 235, 0.05)',
      borderWidth: 2,
      pointBackgroundColor: '#2563EB',
      pointBorderColor: isDark ? '#0B0F19' : '#FFFFFF',
      pointHoverBackgroundColor: '#FFFFFF',
      pointHoverBorderColor: '#2563EB',
      pointRadius: 4,
      pointHoverRadius: 6,
      fill: true,
      tension: 0.35,
      borderDash: [5, 5]
    }]
  };
  
  trajectoryChart = new Chart(ctx, {
    type: 'line',
    data: data,
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'top',
          labels: {
            color: textColor,
            font: { family: 'Inter', size: 12, weight: 600 }
          }
        },
        tooltip: {
          padding: 12,
          font: { family: 'Inter' }
        }
      },
      scales: {
        x: {
          grid: { color: gridColor },
          ticks: { color: textColor, font: { family: 'Inter', size: 10 } }
        },
        y: {
          min: 91.0,
          max: 95.5,
          grid: { color: gridColor },
          ticks: { color: textColor, font: { family: 'Inter', size: 10 }, stepSize: 1.0 }
        }
      }
    }
  });
}

// ===== INITIATE ON DOM CONTENT LOADED =====
document.addEventListener('DOMContentLoaded', () => {
  // Navigation binding
  document.querySelectorAll('[data-slide]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const idx = parseInt(btn.dataset.slide);
      goToSlide(idx);
    });
  });
  
  initTheme();
  renderCharts();
});
