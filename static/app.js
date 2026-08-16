/**
 * GitHub Repo Analyzer — Web Frontend Client Logic
 */

document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const form = document.getElementById('analyzeForm');
  const input = document.getElementById('repoUrlInput');
  const submitBtn = document.getElementById('submitBtn');
  const sampleChips = document.querySelectorAll('.chip');

  // Sections
  const loadingSection = document.getElementById('loadingSection');
  const errorSection = document.getElementById('errorSection');
  const resultsSection = document.getElementById('resultsSection');
  const errorMessage = document.getElementById('errorMessage');
  const btnRetry = document.getElementById('btnRetry');

  // Loading Elements
  const loadingTitle = document.getElementById('loadingTitle');
  const loadingRepoName = document.getElementById('loadingRepoName');
  const elapsedTimer = document.getElementById('elapsedTimer');
  const progressBar = document.getElementById('progressBar');

  // Results Elements
  const resRepoFullName = document.getElementById('resRepoFullName');
  const resRepoLink = document.getElementById('resRepoLink');
  const resRepoDesc = document.getElementById('resRepoDesc');
  const resStars = document.getElementById('resStars');
  const resForks = document.getElementById('resForks');
  const resOpenIssues = document.getElementById('resOpenIssues');
  const resLanguage = document.getElementById('resLanguage');
  const resLicense = document.getElementById('resLicense');

  const resOverallScore = document.getElementById('resOverallScore');
  const scoreGaugeFill = document.getElementById('scoreGaugeFill');
  const resOverallGrade = document.getElementById('resOverallGrade');
  const resAnalyzedAt = document.getElementById('resAnalyzedAt');
  const resExecutiveSummary = document.getElementById('resExecutiveSummary');
  const resTopStrengths = document.getElementById('resTopStrengths');
  const resTopIssues = document.getElementById('resTopIssues');

  const categoriesGrid = document.getElementById('categoriesGrid');
  const recommendationsList = document.getElementById('recommendationsList');
  const filterPills = document.querySelectorAll('#priorityFilterPills .filter-btn');

  // Export & MCP Modal
  const btnCopyMarkdown = document.getElementById('btnCopyMarkdown');
  const btnDownloadJson = document.getElementById('btnDownloadJson');
  const btnViewMcpConfig = document.getElementById('btnViewMcpConfig');
  const btnOpenMcpModal = document.getElementById('btnOpenMcpModal');
  const btnCloseMcpModal = document.getElementById('btnCloseMcpModal');
  const mcpModal = document.getElementById('mcpModal');
  const toastNotification = document.getElementById('toastNotification');
  const toastText = document.getElementById('toastText');

  let currentResult = null;
  let timerInterval = null;
  let stepInterval = null;
  let activeFilter = 'all';

  // Category Configuration
  const CATEGORY_CONFIG = {
    code_quality: { name: 'Code Quality', icon: 'fa-code', color: 'var(--cyan)' },
    documentation: { name: 'Documentation', icon: 'fa-book', color: 'var(--blue)' },
    testing: { name: 'Testing Coverage', icon: 'fa-vial-circle-check', color: 'var(--emerald)' },
    security: { name: 'Security & Auth', icon: 'fa-shield-halved', color: 'var(--rose)' },
    ci_cd: { name: 'CI/CD Automation', icon: 'fa-rocket', color: 'var(--indigo)' },
    project_structure: { name: 'Architecture & Layout', icon: 'fa-sitemap', color: 'var(--cyan)' },
    dependencies: { name: 'Dependencies', icon: 'fa-cubes', color: 'var(--amber)' },
    best_practices: { name: 'Best Practices', icon: 'fa-award', color: 'var(--emerald)' }
  };

  // ── Normalize GitHub Input ──────────────────────────────────────────────
  function normalizeRepoUrl(raw) {
    let text = raw.trim();
    if (!text) return '';
    if (!text.startsWith('http://') && !text.startsWith('https://')) {
      if (text.includes('github.com/')) {
        text = 'https://' + text;
      } else {
        // e.g. "pallets/click"
        text = `https://github.com/${text}`;
      }
    }
    return text.replace(/\.git$/, '').replace(/\/$/, '');
  }

  // ── Progress Stepper Simulation ─────────────────────────────────────────
  function startProgressTracker(repoUrl) {
    loadingRepoName.textContent = repoUrl;
    let seconds = 0;
    elapsedTimer.textContent = '0s';
    progressBar.style.width = '10%';

    // Reset steps
    for (let i = 1; i <= 5; i++) {
      const step = document.getElementById(`step-${i}`);
      step.className = 'step-item';
      step.querySelector('.step-indicator').innerHTML = '<i class="fa-regular fa-circle"></i>';
    }

    const setStepActive = (stepNum, percent) => {
      progressBar.style.width = `${percent}%`;
      for (let i = 1; i < stepNum; i++) {
        const prev = document.getElementById(`step-${i}`);
        prev.className = 'step-item done';
        prev.querySelector('.step-indicator').innerHTML = '<i class="fa-solid fa-check"></i>';
      }
      const cur = document.getElementById(`step-${stepNum}`);
      cur.className = 'step-item active';
      cur.querySelector('.step-indicator').innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
    };

    setStepActive(1, 20);

    timerInterval = setInterval(() => {
      seconds++;
      elapsedTimer.textContent = `${seconds}s`;

      if (seconds === 8)  setStepActive(2, 40);
      if (seconds === 16) setStepActive(3, 65);
      if (seconds === 28) setStepActive(4, 85);
      if (seconds === 36) setStepActive(5, 95);
    }, 1000);
  }

  function stopProgressTracker() {
    if (timerInterval) clearInterval(timerInterval);
    if (stepInterval) clearInterval(stepInterval);
  }

  // ── Execute Analysis ───────────────────────────────────────────────────
  async function runAnalysis(repoUrl) {
    const cleanUrl = normalizeRepoUrl(repoUrl);
    if (!cleanUrl) return;

    // UI state
    errorSection.classList.add('hidden');
    resultsSection.classList.add('hidden');
    loadingSection.classList.remove('hidden');
    submitBtn.disabled = true;
    input.value = cleanUrl;

    startProgressTracker(cleanUrl);

    try {
      const response = await fetch('/api/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({ repo_url: cleanUrl })
      });

      const data = await response.json();

      if (!response.ok || data.error) {
        throw new Error(data.error || `Server responded with status ${response.status}`);
      }

      currentResult = data;
      renderResults(data);

      stopProgressTracker();
      loadingSection.classList.add('hidden');
      resultsSection.classList.remove('hidden');

      // Smooth scroll to results
      resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

    } catch (err) {
      stopProgressTracker();
      loadingSection.classList.add('hidden');
      errorMessage.textContent = err.message || 'Failed to complete analysis. Please verify the repository URL and your API keys.';
      errorSection.classList.remove('hidden');
    } finally {
      submitBtn.disabled = false;
    }
  }

  // ── Render Results ─────────────────────────────────────────────────────
  function renderResults(data) {
    const meta = data.repo_metadata || {};
    
    // Header & Meta
    resRepoFullName.textContent = data.repo_full_name || 'Repository';
    resRepoLink.href = `https://github.com/${data.repo_full_name}`;
    resRepoDesc.textContent = meta.description || 'No description provided by repository.';
    
    resStars.textContent = (meta.stars || 0).toLocaleString();
    resForks.textContent = (meta.forks || 0).toLocaleString();
    resOpenIssues.textContent = (meta.open_issues || 0).toLocaleString();
    resLanguage.textContent = meta.primary_language || 'Various';
    resLicense.textContent = meta.license || 'None';

    // Overall Score & Grade
    const score = data.overall_score || 0;
    const grade = data.overall_grade || 'C';
    
    animateCounter(resOverallScore, score);
    setOverallGrade(grade);
    setGaugeValue(score);

    resAnalyzedAt.textContent = data.analyzed_at ? new Date(data.analyzed_at).toLocaleString() : 'Just now';
    resExecutiveSummary.textContent = data.executive_summary || '';

    // Strengths & Issues
    resTopStrengths.innerHTML = (data.top_strengths || [])
      .map(s => `<li>${escapeHtml(s)}</li>`)
      .join('') || '<li>No specific strengths recorded.</li>';

    resTopIssues.innerHTML = (data.top_issues || [])
      .map(i => `<li>${escapeHtml(i)}</li>`)
      .join('') || '<li>No critical issues recorded.</li>';

    // 8 Categories
    renderCategoryGrid(data);

    // Prioritized Recommendations
    renderRecommendations(data.prioritized_recommendations || []);
  }

  function setOverallGrade(grade) {
    resOverallGrade.textContent = grade;
    resOverallGrade.className = 'grade-pill';
    const g = grade.charAt(0).toUpperCase();
    if (g === 'A') resOverallGrade.classList.add('grade-a');
    else if (g === 'B') resOverallGrade.classList.add('grade-b');
    else if (g === 'C') resOverallGrade.classList.add('grade-c');
    else resOverallGrade.classList.add('grade-d');
  }

  function setGaugeValue(score) {
    // 2 * PI * 70 ≈ 440
    const circumference = 440;
    const offset = circumference - (circumference * score) / 100;
    scoreGaugeFill.style.strokeDashoffset = offset;

    // Color gradient based on score
    if (score >= 85) scoreGaugeFill.style.stroke = 'var(--emerald)';
    else if (score >= 70) scoreGaugeFill.style.stroke = 'var(--cyan)';
    else if (score >= 50) scoreGaugeFill.style.stroke = 'var(--amber)';
    else scoreGaugeFill.style.stroke = 'var(--rose)';
  }

  function animateCounter(elem, target) {
    let current = 0;
    const step = Math.max(1, Math.floor(target / 30));
    const timer = setInterval(() => {
      current += step;
      if (current >= target) {
        current = target;
        clearInterval(timer);
      }
      elem.textContent = current;
    }, 25);
  }

  function renderCategoryGrid(data) {
    categoriesGrid.innerHTML = '';
    const keys = Object.keys(CATEGORY_CONFIG);

    keys.forEach(key => {
      const cat = data[key];
      if (!cat) return;

      const conf = CATEGORY_CONFIG[key];
      const score = cat.score || 0;
      const grade = cat.grade || 'N/A';

      // Bar color
      let barColor = 'var(--emerald)';
      let gradeClass = 'grade-a';
      if (score < 50) { barColor = 'var(--rose)'; gradeClass = 'grade-d'; }
      else if (score < 70) { barColor = 'var(--amber)'; gradeClass = 'grade-c'; }
      else if (score < 85) { barColor = 'var(--cyan)'; gradeClass = 'grade-b'; }

      const card = document.createElement('div');
      card.className = 'glass-card category-card';
      card.innerHTML = `
        <div>
          <div class="cat-header">
            <div class="cat-title-group">
              <div class="cat-icon" style="color:${conf.color};">
                <i class="fa-solid ${conf.icon}"></i>
              </div>
              <span class="cat-name">${conf.name}</span>
            </div>
            <span class="cat-grade-badge ${gradeClass}">${grade}</span>
          </div>

          <div class="cat-meter-wrap">
            <div class="cat-meter-header">
              <span class="cat-score-text" style="color:${barColor};">${score}/100</span>
            </div>
            <div class="cat-progress-track">
              <div class="cat-progress-fill" style="width: ${score}%; background: ${barColor};"></div>
            </div>
          </div>

          <p class="cat-summary">${escapeHtml(cat.summary || '')}</p>
        </div>

        <div>
          <button type="button" class="cat-accordion-toggle" onclick="this.nextElementSibling.classList.toggle('hidden')">
            <span>Details & Actions (${(cat.issues || []).length + (cat.recommendations || []).length})</span>
            <i class="fa-solid fa-chevron-down"></i>
          </button>
          <div class="cat-accordion-content hidden">
            ${(cat.issues && cat.issues.length) ? `
              <div>
                <strong style="color:var(--amber);">Identified Gaps:</strong>
                <ul class="bullet-list" style="margin-top:0.3rem;">
                  ${cat.issues.map(i => `<li>${escapeHtml(i)}</li>`).join('')}
                </ul>
              </div>
            ` : ''}
            ${(cat.recommendations && cat.recommendations.length) ? `
              <div style="margin-top:0.5rem;">
                <strong style="color:var(--emerald);">Recommendations:</strong>
                <ul class="bullet-list" style="margin-top:0.3rem;">
                  ${cat.recommendations.map(r => `<li>${escapeHtml(r)}</li>`).join('')}
                </ul>
              </div>
            ` : ''}
          </div>
        </div>
      `;

      categoriesGrid.appendChild(card);
    });
  }

  function renderRecommendations(recs) {
    recommendationsList.innerHTML = '';

    const filtered = recs.filter(r => {
      if (activeFilter === 'all') return true;
      return (r.priority || '').toLowerCase() === activeFilter;
    });

    if (filtered.length === 0) {
      recommendationsList.innerHTML = `
        <div class="glass-card" style="padding:1.5rem; text-align:center; color:var(--text-muted);">
          No recommendations found for priority "${activeFilter}".
        </div>
      `;
      return;
    }

    filtered.forEach(rec => {
      const p = (rec.priority || 'medium').toLowerCase();
      let priorityClass = 'med';
      if (p === 'critical') priorityClass = 'crit';
      else if (p === 'high') priorityClass = 'high';
      else if (p === 'low') priorityClass = 'low';

      const card = document.createElement('div');
      card.className = `glass-card rec-item-card ${priorityClass}`;
      card.innerHTML = `
        <div class="rec-body">
          <div class="rec-meta-row">
            <span class="priority-pill ${priorityClass}">${p.toUpperCase()}</span>
            <span class="category-tag"><i class="fa-solid fa-tag"></i> ${escapeHtml(rec.category || 'General')}</span>
            <span class="effort-tag"><i class="fa-solid fa-gauge"></i> Effort: ${(rec.effort || 'Medium').toUpperCase()}</span>
          </div>
          <h4 class="rec-title">${escapeHtml(rec.title || '')}</h4>
          <p class="rec-desc">${escapeHtml(rec.description || '')}</p>
        </div>
      `;
      recommendationsList.appendChild(card);
    });
  }

  // ── Filter Buttons ─────────────────────────────────────────────────────
  filterPills.forEach(btn => {
    btn.addEventListener('click', () => {
      filterPills.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeFilter = btn.getAttribute('data-filter');
      if (currentResult) {
        renderRecommendations(currentResult.prioritized_recommendations || []);
      }
    });
  });

  // ── Sample Chips Click ─────────────────────────────────────────────────
  sampleChips.forEach(chip => {
    chip.addEventListener('click', () => {
      const repo = chip.getAttribute('data-repo');
      input.value = repo;
      runAnalysis(repo);
    });
  });

  // ── Form Submit ────────────────────────────────────────────────────────
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    runAnalysis(input.value);
  });

  btnRetry.addEventListener('click', () => {
    if (input.value) runAnalysis(input.value);
  });

  // ── Export Handlers ────────────────────────────────────────────────────
  btnCopyMarkdown.addEventListener('click', () => {
    if (!currentResult) return;
    const md = buildMarkdownReport(currentResult);
    navigator.clipboard.writeText(md).then(() => {
      showToast('Markdown report copied to clipboard!');
    });
  });

  btnDownloadJson.addEventListener('click', () => {
    if (!currentResult) return;
    const blob = new Blob([JSON.stringify(currentResult, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    const safeName = (currentResult.repo_full_name || 'repo').replace(/[\/\\]/g, '-');
    a.href = url;
    a.download = `github-audit-${safeName}.json`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('JSON report downloaded!');
  });

  // ── MCP Modal ──────────────────────────────────────────────────────────
  const openModal = () => {
    // Dynamically adjust remote URL to match current hostname
    const currentOrigin = window.location.origin;
    const remoteCode = document.getElementById('codeRemoteMcp');
    if (remoteCode) {
      remoteCode.textContent = JSON.stringify({
        mcpServers: {
          "github-analyzer": {
            url: `${currentOrigin}/mcp`,
            transport: "http"
          }
        }
      }, null, 2);
    }
    mcpModal.classList.remove('hidden');
  };

  const closeModal = () => {
    mcpModal.classList.add('hidden');
  };

  btnOpenMcpModal.addEventListener('click', openModal);
  btnViewMcpConfig.addEventListener('click', openModal);
  btnCloseMcpModal.addEventListener('click', closeModal);
  mcpModal.addEventListener('click', (e) => {
    if (e.target === mcpModal) closeModal();
  });

  // Modal Tabs
  const modalTabs = document.querySelectorAll('.modal-tab');
  modalTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      modalTabs.forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
      tab.classList.add('active');
      const targetId = tab.getAttribute('data-tab');
      document.getElementById(targetId).classList.add('active');
    });
  });

  // Copy Code Buttons inside Modal
  document.querySelectorAll('.btn-copy-code').forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-target');
      const text = document.getElementById(targetId).textContent;
      navigator.clipboard.writeText(text).then(() => {
        showToast('MCP config copied to clipboard!');
      });
    });
  });

  // ── Utilities ──────────────────────────────────────────────────────────
  function showToast(msg) {
    toastText.textContent = msg;
    toastNotification.classList.remove('hidden');
    setTimeout(() => {
      toastNotification.classList.add('hidden');
    }, 3000);
  }

  function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;')
              .replace(/</g, '&lt;')
              .replace(/>/g, '&gt;')
              .replace(/"/g, '&quot;')
              .replace(/'/g, '&#039;');
  }

  function buildMarkdownReport(data) {
    let md = `# GitHub Repository Audit: ${data.repo_full_name}\n\n`;
    md += `**Overall Score:** ${data.overall_score}/100 (${data.overall_grade})\n`;
    md += `**Analyzed At:** ${data.analyzed_at}\n\n`;
    md += `## Executive Summary\n${data.executive_summary}\n\n`;
    
    md += `## Top Strengths\n`;
    (data.top_strengths || []).forEach(s => { md += `- ${s}\n`; });
    md += `\n## Areas for Improvement\n`;
    (data.top_issues || []).forEach(i => { md += `- ${i}\n`; });
    
    md += `\n## 8-Category Scorecard\n`;
    md += `| Category | Score | Grade | Summary |\n|---|---|---|---|\n`;
    Object.keys(CATEGORY_CONFIG).forEach(k => {
      const c = data[k];
      if (c) md += `| ${CATEGORY_CONFIG[k].name} | ${c.score}/100 | ${c.grade} | ${c.summary} |\n`;
    });

    md += `\n## Prioritized Action Plan\n`;
    (data.prioritized_recommendations || []).forEach(r => {
      md += `### [${(r.priority || 'MED').toUpperCase()}] ${r.title} (${r.category} — Effort: ${r.effort})\n`;
      md += `${r.description}\n\n`;
    });

    return md;
  }
});
