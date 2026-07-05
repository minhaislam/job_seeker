/* ===== CV Upload ===== */
let cvUploaded = false;

const cvFileInput   = document.getElementById('cv-file-input');
const cvUploadBtn   = document.getElementById('cv-upload-btn');
const cvUploadArea  = document.getElementById('cv-upload-area');
const cvLoadedArea  = document.getElementById('cv-loaded-area');
const cvRemoveBtn   = document.getElementById('cv-remove-btn');

cvFileInput.addEventListener('change', () => {
  cvUploadBtn.disabled = !cvFileInput.files.length;
});

cvUploadBtn.addEventListener('click', async () => {
  const file = cvFileInput.files[0];
  if (!file) return;

  cvUploadBtn.textContent = 'Uploading…';
  cvUploadBtn.disabled = true;

  try {
    const fd = new FormData();
    fd.append('file', file);
    const resp = await fetch('/api/cv', { method: 'POST', body: fd });
    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || 'Upload failed');
    }
    const data = await resp.json();
    setCvLoaded(true, data.chars);
  } catch (e) {
    alert('CV upload failed: ' + e.message);
    cvUploadBtn.textContent = 'Upload CV';
    cvUploadBtn.disabled = false;
  }
});

cvRemoveBtn.addEventListener('click', () => {
  cvFileInput.value = '';
  cvUploadBtn.disabled = true;
  cvUploadBtn.textContent = 'Upload CV';
  setCvLoaded(false, 0);
});

function setCvLoaded(loaded, chars) {
  cvUploaded = loaded;
  cvUploadArea.classList.toggle('hidden', loaded);
  cvLoadedArea.classList.toggle('hidden', !loaded);
}

(async () => {
  try {
    const resp = await fetch('/api/cv/status');
    const data = await resp.json();
    if (data.uploaded) setCvLoaded(true, data.chars || 0);
  } catch {}
})();

/* ===== State ===== */
let allJobs = [];
let currentJob = null;

/* ===== DOM Refs ===== */
const form        = document.getElementById('search-form');
const queryInput  = document.getElementById('query-input');
const searchBtn   = document.getElementById('search-btn');
const btnLabel    = document.getElementById('btn-label');
const btnSpinner  = document.getElementById('btn-spinner');
const resultsSection = document.getElementById('results-section');
const jobList     = document.getElementById('job-list');
const resultsCount = document.getElementById('results-count');
const sortSelect  = document.getElementById('sort-select');
const emptyState  = document.getElementById('empty-state');
const modalOverlay = document.getElementById('modal-overlay');
const modalClose  = document.getElementById('modal-close');

/* ===== Search ===== */
form.addEventListener('submit', e => { e.preventDefault(); doSearch(); });

document.querySelectorAll('.quick-tag').forEach(btn => {
  btn.addEventListener('click', () => {
    queryInput.value = btn.dataset.q;
    doSearch();
  });
});

async function doSearch() {
  const query = queryInput.value.trim();
  if (!query) return;

  setLoading(true);
  resultsSection.classList.add('hidden');
  emptyState.classList.add('hidden');

  try {
    const resp = await fetch('/api/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, limit: 20 }),
    });
    if (!resp.ok) throw new Error(`Server error: ${resp.status}`);
    const data = await resp.json();

    allJobs = data.jobs || [];
    renderJobs();
  } catch (err) {
    console.error(err);
    alert('Search failed: ' + err.message);
  } finally {
    setLoading(false);
  }
}

function setLoading(loading) {
  searchBtn.disabled = loading;
  btnLabel.textContent = loading ? 'Searching...' : 'Search Jobs';
  btnSpinner.classList.toggle('hidden', !loading);
}

/* ===== Render Jobs ===== */
sortSelect.addEventListener('change', renderJobs);

function renderJobs() {
  const sorted = [...allJobs];
  const by = sortSelect.value;

  if (by === 'match') sorted.sort((a, b) => (b.match_score || 0) - (a.match_score || 0));
  else if (by === 'date') sorted.sort((a, b) => (b.published_at || '').localeCompare(a.published_at || ''));
  else if (by === 'company') sorted.sort((a, b) => a.company.localeCompare(b.company));

  jobList.innerHTML = '';

  if (sorted.length === 0) {
    emptyState.classList.remove('hidden');
    resultsSection.classList.add('hidden');
    return;
  }

  emptyState.classList.add('hidden');
  resultsSection.classList.remove('hidden');
  resultsCount.textContent = `${sorted.length} jobs found`;

  sorted.forEach(job => {
    const card = buildCard(job);
    card.addEventListener('click', () => openModal(job));
    jobList.appendChild(card);
  });
}

function buildCard(job) {
  const card = document.createElement('div');
  card.className = 'job-card';
  card.dataset.jobId = job.id;

  const scoreHTML = job.match_score != null
    ? `<div class="score-ring ${scoreColor(job.match_score)}">${job.match_score}<small>%</small></div>`
    : `<div class="score-ring score-none" title="Click to score">?</div>`;

  const visibleTags = (job.tags || []).slice(0, 5);
  const chips = visibleTags.map(t => `<span class="chip">${t}</span>`).join('');
  const salary = job.salary ? `<span>&#128181; ${job.salary}</span>` : '';

  card.innerHTML = `
    <div class="card-left">
      <div class="card-title">${escHtml(job.title)}</div>
      <div class="card-company">${escHtml(job.company)}</div>
      <div class="card-meta">
        <span>&#127759; ${escHtml(job.location)}</span>
        ${salary}
        <span class="badge-source">${escHtml(job.source)}</span>
        ${job.published_at ? `<span>${formatDate(job.published_at)}</span>` : ''}
      </div>
      <div class="card-tags">${chips}</div>
    </div>
    <div class="card-right">${scoreHTML}</div>
  `;
  return card;
}

/* ===== Modal ===== */
modalClose.addEventListener('click', closeModal);
modalOverlay.addEventListener('click', e => { if (e.target === modalOverlay) closeModal(); });
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

async function openModal(job) {
  currentJob = job;
  resetModal();

  document.getElementById('m-title').textContent = job.title;
  document.getElementById('m-company').textContent = job.company;
  document.getElementById('m-location').textContent = job.location;
  document.getElementById('m-source').textContent = job.source;
  document.getElementById('m-salary').innerHTML = job.salary ? '&#128181; ' + escHtml(job.salary) : '';

  // Overview tab
  const tags = (job.tags || []).map(t => `<span class="chip">${escHtml(t)}</span>`).join('');
  document.getElementById('m-tags').innerHTML = tags;
  document.getElementById('m-description').textContent = job.description || 'No description available.';
  document.getElementById('m-apply-link').href = job.url || '#';

  // Show modal immediately with scoring spinner
  const circle = document.getElementById('m-score-circle');
  const scoreNum = document.getElementById('m-score-num');
  const summary = document.getElementById('m-summary');

  if (!cvUploaded) {
    _setScore(circle, scoreNum, null, false);
    summary.textContent = 'Upload your CV above to see match score.';
    renderSkillList('m-matched-skills', []);
    renderSkillList('m-missing-skills', []);
    modalOverlay.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    return;
  }

  _setScore(circle, scoreNum, null, true);
  summary.textContent = 'Analysing match with your CV…';
  renderSkillList('m-matched-skills', []);
  renderSkillList('m-missing-skills', []);

  modalOverlay.classList.remove('hidden');
  document.body.style.overflow = 'hidden';

  // Fetch scored job — triggers lazy scoring on the backend
  console.log('[Score] fetching', job.id);
  try {
    const resp = await fetch(`/api/job/${encodeURIComponent(job.id)}`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const scored = await resp.json();
    console.log('[Score] received', scored.id, 'score:', scored.match_score);

    // Guard: modal may have been closed while scoring
    if (!modalOverlay.classList.contains('hidden') && currentJob && currentJob.id === scored.id) {
      currentJob = scored;
      _setScore(circle, scoreNum, scored.match_score, false);
      document.getElementById('m-summary').textContent = scored.match_summary || 'No match analysis available.';
      renderSkillList('m-matched-skills', scored.matched_skills || []);
      renderSkillList('m-missing-skills', scored.missing_skills || []);
    }

    _updateCardScore(scored.id, scored.match_score);

    const idx = allJobs.findIndex(j => j.id === scored.id);
    if (idx !== -1) allJobs[idx] = scored;
  } catch (e) {
    console.error('[Score] error:', e);
    if (!modalOverlay.classList.contains('hidden') && currentJob && currentJob.id === job.id) {
      _setScore(circle, scoreNum, null, false);
      document.getElementById('m-summary').textContent = 'Scoring failed — check console for details.';
    }
  }
}

function _setScore(circle, scoreNum, score, loading) {
  if (loading) {
    scoreNum.textContent = '…';
    circle.querySelector('small').textContent = 'scoring';
    circle.className = 'm-score-circle score-scoring';
    circle.style.borderColor = '';
    circle.style.color = '';
  } else if (score != null) {
    scoreNum.textContent = score;
    circle.querySelector('small').textContent = 'match';
    circle.className = `m-score-circle ${scoreColor(score)}`;
    circle.style.borderColor = scoreHex(score);
    circle.style.color = scoreHex(score);
  } else {
    scoreNum.textContent = '–';
    circle.querySelector('small').textContent = '';
    circle.className = 'm-score-circle score-none';
    circle.style.borderColor = '';
    circle.style.color = '';
  }
}

function _updateCardScore(jobId, score) {
  const card = document.querySelector(`.job-card[data-job-id="${jobId}"]`);
  if (!card || score == null) return;
  const ring = card.querySelector('.score-ring');
  if (!ring) return;
  ring.className = `score-ring ${scoreColor(score)}`;
  ring.innerHTML = `${score}<small>%</small>`;
  ring.title = '';
}

function closeModal() {
  modalOverlay.classList.add('hidden');
  document.body.style.overflow = '';
  currentJob = null;
}

function resetModal() {
  // Reset tabs to overview
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelector('[data-tab="overview"]').classList.add('active');
  document.querySelectorAll('.tab-content').forEach(t => t.classList.add('hidden'));
  document.getElementById('tab-overview').classList.remove('hidden');

  // Reset cover letter
  document.getElementById('cover-idle').classList.remove('hidden');
  document.getElementById('cover-loading').classList.add('hidden');
  document.getElementById('cover-output').classList.add('hidden');
  document.getElementById('cover-text').value = '';
}

/* ===== Tabs ===== */
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('.tab-content').forEach(t => t.classList.add('hidden'));
    document.getElementById(`tab-${btn.dataset.tab}`).classList.remove('hidden');
  });
});

/* ===== Cover Letter ===== */
document.getElementById('gen-cover-btn').addEventListener('click', generateCoverLetter);
document.getElementById('regen-btn').addEventListener('click', generateCoverLetter);

document.getElementById('copy-btn').addEventListener('click', () => {
  const text = document.getElementById('cover-text').value;
  navigator.clipboard.writeText(text).then(() => {
    const btn = document.getElementById('copy-btn');
    btn.textContent = 'Copied!';
    setTimeout(() => btn.textContent = 'Copy to Clipboard', 2000);
  });
});

async function generateCoverLetter() {
  if (!currentJob) return;

  document.getElementById('cover-idle').classList.add('hidden');
  document.getElementById('cover-output').classList.add('hidden');
  document.getElementById('cover-loading').classList.remove('hidden');

  try {
    const resp = await fetch('/api/cover-letter', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        job_id: currentJob.id,
        job_title: currentJob.title,
        company: currentJob.company,
        description: currentJob.description,
      }),
    });
    if (!resp.ok) throw new Error(`Server error: ${resp.status}`);
    const data = await resp.json();
    document.getElementById('cover-text').value = data.cover_letter;
    document.getElementById('cover-loading').classList.add('hidden');
    document.getElementById('cover-output').classList.remove('hidden');
  } catch (err) {
    document.getElementById('cover-loading').classList.add('hidden');
    document.getElementById('cover-idle').classList.remove('hidden');
    alert('Cover letter generation failed: ' + err.message);
  }
}

/* ===== Helpers ===== */
function renderSkillList(id, skills) {
  const el = document.getElementById(id);
  el.innerHTML = skills.length
    ? skills.map(s => `<li>${escHtml(s)}</li>`).join('')
    : '<li style="color:var(--text-muted);font-style:italic">None identified</li>';
}

function scoreColor(score) {
  if (score == null) return 'score-none';
  if (score >= 75) return 'score-high';
  if (score >= 50) return 'score-mid';
  return 'score-low';
}

function scoreHex(score) {
  if (score == null) return '';
  if (score >= 75) return '#22c55e';
  if (score >= 50) return '#eab308';
  return '#ef4444';
}

function formatDate(str) {
  if (!str) return '';
  try {
    return new Date(str).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
  } catch { return ''; }
}

function escHtml(str) {
  return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
