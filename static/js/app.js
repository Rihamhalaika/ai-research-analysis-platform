/* ═══════════════════════════════════════════════════════════════════════
   SmartResearch Engine — Frontend Logic (app.js)
   ═══════════════════════════════════════════════════════════════════════ */

'use strict';

/* ── State ───────────────────────────────────────────────────────────── */
let allPapers   = [];
let searchData  = null;
let reportText  = '';

/* ── Slider ───────────────────────────────────────────────────────────── */
document.getElementById('paperSlider').addEventListener('input', function () {
  document.getElementById('paperCount').textContent = this.value;
});

/* ── Nav smooth scroll + active link ─────────────────────────────────── */
document.querySelectorAll('.nav-link').forEach(link => {
  link.addEventListener('click', e => {
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    link.classList.add('active');
  });
});

/* ── Enter key on search ──────────────────────────────────────────────── */
document.getElementById('topicInput').addEventListener('keydown', e => {
  if (e.key === 'Enter') startSearch();
});

/* ════════════════════════════════════════════════════════════════════════
   SEARCH FLOW
   ════════════════════════════════════════════════════════════════════════ */

function quickSearch(topic) {
  document.getElementById('topicInput').value = topic;
  startSearch();
}

async function startSearch() {
  const topic      = document.getElementById('topicInput').value.trim();
  const maxPapers  = parseInt(document.getElementById('paperSlider').value);
  if (!topic) return;

  /* UI reset */
  const btn = document.getElementById('searchBtn');
  btn.disabled = true;
  showSection('results');
  hide('resultsContent');
  show('loadingState');
  renderLoadingSteps('loadingSteps', [
    'Querying Semantic Scholar…',
    'Querying arXiv…',
    'Extracting topics & gaps…',
    'Building results…',
  ]);
  activateStep('loadingSteps', 0);

  try {
    activateStep('loadingSteps', 1);
    const resp = await fetch('/api/search', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ topic, max_papers: maxPapers }),
    });
    const data = await resp.json();

    if (data.error) throw new Error(data.error);

    activateStep('loadingSteps', 2);
    searchData = data;
    allPapers  = data.papers || [];

    activateStep('loadingSteps', 3);
    renderSearchResults(data);

  } catch (err) {
    alert('Search failed: ' + err.message);
  } finally {
    hide('loadingState');
    show('resultsContent');
    btn.disabled = false;
  }
}

function renderSearchResults(data) {
  /* Metrics */
  document.getElementById('metricsRow').innerHTML = [
    metric('Papers',   data.papers.length,           'retrieved'),
    metric('Topics',   data.topics.length,            'key themes'),
    metric('Gaps',     data.gaps.gap_topics.length,   'identified'),
    metric('Sources',  [...new Set(data.papers.map(p => p.source))].length, 'databases'),
  ].join('');

  /* Papers */
  renderPapers(data.papers);

  /* Topics chart */
  const tc = document.getElementById('topicsChart');
  const maxC = data.topics[0]?.paper_count || 1;
  tc.innerHTML = data.topics.map(t => `
    <div class="topic-bar-item">
      <div class="topic-bar-label">
        <span>${cap(t.keyword)}</span>
        <span>${t.paper_count} papers</span>
      </div>
      <div class="topic-bar-track">
        <div class="topic-bar-fill" style="width:${t.paper_count / maxC * 100}%"></div>
      </div>
    </div>`).join('') || '<p style="color:var(--dim);font-size:.82rem">No topics extracted.</p>';

  /* Year chart */
  const yd  = data.year_distribution || {};
  const yc  = document.getElementById('yearChart');
  const maxY = Math.max(...Object.values(yd), 1);
  yc.innerHTML = Object.entries(yd).sort((a,b)=>b[0]-a[0]).slice(0,8).map(([y,c]) => `
    <div class="year-bar-item">
      <span class="year-label">${y}</span>
      <div class="year-bar-track">
        <div class="year-bar-fill" style="width:${c/maxY*100}%"></div>
      </div>
      <span class="year-count">${c}</span>
    </div>`).join('') || '<p style="color:var(--dim);font-size:.82rem">No data.</p>';

  /* Gaps */
  const gl  = document.getElementById('gapsList');
  const gaps = data.gaps.gap_topics || [];
  gl.innerHTML = gaps.slice(0, 8).map((g, i) => `
    <div class="gap-item">
      <div class="gap-num">${i + 1}</div>
      <div>
        <div class="gap-kw">${cap(g.keyword)}</div>
        <div class="gap-meta">
          In broader field: ${g.broad_count} papers · In your results: ${g.specific_count}
          · gap score: ${g.gap_score}
        </div>
      </div>
    </div>`).join('') || '<p style="color:var(--dim);font-size:.82rem">No gaps detected.</p>';
}

function renderPapers(papers) {
  allPapers = papers;
  const list = document.getElementById('papersList');
  if (!papers.length) {
    list.innerHTML = '<p style="color:var(--dim);font-size:.85rem">No papers found.</p>';
    return;
  }
  list.innerHTML = papers.map((p, i) => `
    <div class="paper-card" onclick="openModal(${i})">
      <div class="paper-title">${p.title}</div>
      <div class="paper-meta">
        <span>📅 ${p.year || 'N/A'}</span>
        <span>👤 ${(p.authors || []).slice(0,2).join(', ') || 'Unknown'}</span>
        <span>⭐ ${(p.citations || 0).toLocaleString()}</span>
        <span class="paper-source">${p.source}</span>
      </div>
      <div class="paper-abstract">${p.abstract || 'No abstract available.'}</div>
    </div>`).join('');
}

function filterPapers() {
  const q = document.getElementById('paperFilter').value.toLowerCase();
  const filtered = allPapers.filter(p =>
    (p.title || '').toLowerCase().includes(q) ||
    (p.abstract || '').toLowerCase().includes(q) ||
    (p.authors || []).join(' ').toLowerCase().includes(q)
  );
  renderPapers(filtered);
}

function sortPapers() {
  const by  = document.getElementById('sortBy').value;
  const sorted = [...allPapers].sort((a, b) => {
    if (by === 'year')      return (b.year || 0) - (a.year || 0);
    if (by === 'citations') return (b.citations || 0) - (a.citations || 0);
    return 0;
  });
  renderPapers(sorted);
}

/* ── Paper modal ──────────────────────────────────────────────────────── */
function openModal(idx) {
  const p = allPapers[idx];
  if (!p) return;
  document.getElementById('modalContent').innerHTML = `
    <div class="modal-title">${p.title}</div>
    <div class="modal-meta">
      <span>📅 ${p.year || 'N/A'}</span>
      <span>👤 ${(p.authors || []).join(', ') || 'Unknown'}</span>
      <span>⭐ ${(p.citations || 0).toLocaleString()} citations</span>
      <span class="paper-source">${p.source}</span>
      ${p.venue ? `<span>📰 ${p.venue}</span>` : ''}
      ${p.doi   ? `<a href="https://doi.org/${p.doi}" target="_blank">DOI →</a>` : ''}
    </div>
    <div class="modal-abstract">${p.abstract || 'No abstract available.'}</div>`;
  show('paperModal');
}
function closeModal() { hide('paperModal'); }

/* ── Report ───────────────────────────────────────────────────────────── */
async function generateReport() {
  if (!searchData) return;
  const el = document.getElementById('reportContent');
  el.innerHTML = '<p style="color:var(--muted)">Generating report…</p>';
  try {
    const resp = await fetch('/api/report', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(searchData),
    });
    const data = await resp.json();
    if (data.error) throw new Error(data.error);
    reportText = data.report;
    el.innerHTML = `<pre class="report-text">${escHtml(reportText)}</pre>`;
    document.getElementById('downloadBtn').style.display = 'inline-flex';
  } catch (err) {
    el.innerHTML = `<p style="color:#f87171">Error: ${err.message}</p>`;
  }
}

function downloadReport() {
  if (!reportText) return;
  const blob = new Blob([reportText], { type: 'text/markdown' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url;
  a.download = 'smartresearch-report.md';
  a.click();
  URL.revokeObjectURL(url);
}

function copyReport() {
  if (!reportText) return;
  navigator.clipboard.writeText(reportText).then(() => toast('Report copied!'));
}

/* ════════════════════════════════════════════════════════════════════════
   UPLOAD / PDF ANALYSIS FLOW
   ════════════════════════════════════════════════════════════════════════ */

/* Drag & drop */
function handleDragOver(e) {
  e.preventDefault();
  document.getElementById('uploadZone').classList.add('drag');
}
document.getElementById('uploadZone').addEventListener('dragleave', () => {
  document.getElementById('uploadZone').classList.remove('drag');
});
function handleDrop(e) {
  e.preventDefault();
  document.getElementById('uploadZone').classList.remove('drag');
  const file = e.dataTransfer.files[0];
  if (file) processFile(file);
}

function uploadPDF(e) {
  const file = e.target.files[0];
  if (file) processFile(file);
}

function processFile(file) {
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    alert('Please upload a PDF file.');
    return;
  }

  /* Show file strip */
  document.getElementById('fileName').textContent = file.name;
  document.getElementById('fileSize').textContent = (file.size / 1_048_576).toFixed(2) + ' MB';
  show('fileStrip');
  document.getElementById('fileStrip').classList.remove('hidden');

  /* Immediately start upload */
  sendFileToServer(file);
}

function clearUpload() {
  document.getElementById('pdfInput').value = '';
  document.getElementById('fileStrip').classList.add('hidden');
  hide('pdfResults');
}

async function sendFileToServer(file) {
  /* Show PDF results section with loading */
  showSection('pdfResults');
  hide('pdfContent');
  show('pdfLoadingState');
  renderLoadingSteps('pdfLoadingSteps', [
    'Uploading PDF…',
    'Extracting text from pages…',
    'Detecting paper structure…',
    'Building ordered abstraction…',
  ]);
  activateStep('pdfLoadingSteps', 0);

  try {
    const formData = new FormData();
    formData.append('file', file);

    activateStep('pdfLoadingSteps', 1);
    const resp = await fetch('/api/upload', { method: 'POST', body: formData });
    const data = await resp.json();

    if (data.error) throw new Error(data.error);

    activateStep('pdfLoadingSteps', 2);
    activateStep('pdfLoadingSteps', 3);

    renderPDFResults(data);

  } catch (err) {
    alert('Upload failed: ' + err.message);
  } finally {
    hide('pdfLoadingState');
    show('pdfContent');
  }
}

/* ── Render PDF results ──────────────────────────────────────────────── */
function renderPDFResults(data) {

  /* ── Header ── */
  document.getElementById('pdfTitle').textContent = data.title || data.filename;
  document.getElementById('pdfMeta').textContent  =
    `${(data.word_count || 0).toLocaleString()} words  ·  ${(data.sections || []).length} sections detected`;

  /* ── Section pills ── */
  const pillsEl = document.getElementById('pdfSections');
  pillsEl.innerHTML = (data.sections || []).map(s =>
    `<span class="section-pill">${escHtml(s)}</span>`
  ).join('');

  /* ── Rebuild Tab Bar ── */
  const tabBar = document.querySelector('.pdf-tab-bar');
  tabBar.innerHTML = `
    <button class="pdf-tab active" data-tab="abstraction" onclick="switchTab('abstraction',this)">📋 Section Breakdown</button>
    <button class="pdf-tab" data-tab="overview"     onclick="switchTab('overview',this)">🔑 Key Findings</button>
    <button class="pdf-tab" data-tab="topics"       onclick="switchTab('topics',this)">☁️ Topics &amp; Gaps</button>
  `;

  /* ── TAB 1: Section-by-section abstraction ── */
  const blocks = data.abstraction || [];
  document.getElementById('abstractionBlocks').innerHTML = blocks.length > 0
    ? blocks.map(b => `
        <div style="background:var(--color-surface,#f8f9fa);border-left:4px solid var(--color-accent,#1ABC9C);
                    border-radius:6px;padding:1rem 1.2rem;margin-bottom:1rem;">
          <div style="font-size:.78rem;font-weight:700;color:var(--color-accent,#1ABC9C);
                      text-transform:uppercase;letter-spacing:.06em;margin-bottom:.4rem;">
            ${b.number ? b.number + '. ' : ''}${escHtml(b.label || '')}
          </div>
          <p style="font-size:.92rem;line-height:1.65;color:var(--color-text-primary,#1A252F);margin:0;">
            ${escHtml(b.text || '')}
          </p>
        </div>`).join('')
    : '<p style="color:var(--dim,#888);padding:1rem">No sections could be extracted. Make sure the PDF is text-based, not a scanned image.</p>';

  /* ── TAB 2: Key Findings + stats ── */
  const findings = data.findings || [];
  document.getElementById('overviewStats').innerHTML = `
    <div class="overview-stat"><div class="overview-stat-label">Words</div>
      <div class="overview-stat-value">${(data.word_count||0).toLocaleString()}</div></div>
    <div class="overview-stat"><div class="overview-stat-label">Sections</div>
      <div class="overview-stat-value">${(data.sections||[]).length}</div></div>
    <div class="overview-stat"><div class="overview-stat-label">Key Findings</div>
      <div class="overview-stat-value">${findings.length}</div></div>
    <div class="overview-stat"><div class="overview-stat-label">Gap Sentences</div>
      <div class="overview-stat-value">${(data.gaps||[]).length}</div></div>
  `;
  document.getElementById('pdfFindings').innerHTML = findings.length > 0
    ? findings.map(f => `
        <div style="display:flex;gap:.6rem;align-items:flex-start;padding:.55rem 0;
                    border-bottom:1px solid var(--color-border,#eee);">
          <span style="color:#1ABC9C;font-weight:700;flex-shrink:0;margin-top:.1rem;">✦</span>
          <p style="margin:0;font-size:.9rem;line-height:1.55;color:var(--color-text-primary,#1A252F);">
            ${escHtml(f)}
          </p>
        </div>`).join('')
    : '<p style="color:var(--dim,#888);font-size:.85rem;">No key findings sentences detected.</p>';

  /* ── TAB 3: Topics cloud + Gaps ── */
  const topics = data.topics || [];
  document.getElementById('pdfKeywords').innerHTML = topics.length > 0
    ? topics.map(t => {
        const size = Math.max(0.75, Math.min(1.3, 0.75 + (t.count / 10)));
        return `<span style="display:inline-block;background:var(--color-accent-soft,#EAF4FB);
                  color:var(--color-accent,#1B4F72);border-radius:20px;padding:.3rem .75rem;
                  margin:.25rem;font-size:${size}rem;font-weight:600;">
                  ${escHtml(t.keyword)} <span style="opacity:.6;font-size:.8em;">${t.count}</span>
                </span>`;
      }).join('')
    : '<p style="color:var(--dim,#888);font-size:.85rem;">No topics extracted.</p>';

  const gaps = data.gaps || [];
  document.getElementById('pdfGaps').innerHTML = gaps.length > 0
    ? gaps.map((g, i) => `
        <div style="display:flex;gap:.6rem;align-items:flex-start;padding:.55rem 0;
                    border-bottom:1px solid var(--color-border,#eee);">
          <span style="background:#E67E22;color:#fff;border-radius:50%;width:1.3rem;height:1.3rem;
                       display:flex;align-items:center;justify-content:center;
                       font-size:.7rem;font-weight:700;flex-shrink:0;">${i+1}</span>
          <p style="margin:0;font-size:.88rem;line-height:1.55;color:var(--color-text-primary,#1A252F);">
            ${escHtml(g)}
          </p>
        </div>`).join('')
    : '<p style="color:var(--dim,#888);font-size:.85rem;">No gap/future-work sentences found.</p>';

  /* ── Show section breakdown tab by default ── */
  switchTab('abstraction', document.querySelector('[data-tab="abstraction"]'));
}

/* ── Tab switching ────────────────────────────────────────────────────── */
function switchTab(tabName, btn) {
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.pdf-tab').forEach(b => b.classList.remove('active'));
  const panel = document.getElementById('tab-' + tabName);
  if (panel) panel.classList.add('active');
  if (btn)   btn.classList.add('active');
}

/* ════════════════════════════════════════════════════════════════════════
   UTILITIES
   ════════════════════════════════════════════════════════════════════════ */

function show(id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove('hidden');
}
function hide(id) {
  const el = document.getElementById(id);
  if (el) el.classList.add('hidden');
}
function showSection(id) {
  ['results', 'pdfResults'].forEach(s => hide(s));
  show(id);
}

function cap(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}
function escHtml(str) {
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function metric(label, value, sub) {
  return `
    <div class="metric-card">
      <div class="metric-label">${label}</div>
      <div class="metric-value">${value}</div>
      <div class="metric-sub">${sub}</div>
    </div>`;
}

function overviewStat(label, value) {
  return `
    <div class="overview-stat">
      <div class="overview-stat-label">${label}</div>
      <div class="overview-stat-value">${value}</div>
    </div>`;
}

function renderLoadingSteps(containerId, steps) {
  document.getElementById(containerId).innerHTML =
    steps.map((s, i) => `<div class="loading-step" id="${containerId}-step-${i}">• ${s}</div>`).join('');
}

function activateStep(containerId, index) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.querySelectorAll('.loading-step').forEach((el, i) => {
    el.className = 'loading-step' + (i < index ? ' done' : i === index ? ' active' : '');
  });
}

function toast(msg) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.classList.remove('hidden');
  setTimeout(() => el.classList.add('hidden'), 2500);
}