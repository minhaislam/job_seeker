# Frontend Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle the job seeker SPA to a minimal Vercel/Linear-style neutral dark theme with Inter typography and a two-column job card grid.

**Architecture:** Pure CSS/HTML changes — no JS, no backend, no new files. Replace CSS custom properties and component styles in `style.css`. Add Inter font and update logo/CV markup in `index.html`. Four independent visual tasks, each verifiable by opening the browser.

**Tech Stack:** Vanilla CSS, Google Fonts (Inter), HTML

## Global Constraints

- No changes to `app.js`, backend, or any other files
- No new CSS classes — only restyle existing ones
- No framework, no build step — just edit and hard-refresh (`Ctrl+Shift+R`)
- Accent color: `#3b82f6` (blue) — used consistently, nowhere else
- `--surface2` and `--accent-light` tokens are removed entirely
- Two-column grid breakpoint: `768px`

---

### Task 1: Tokens, Font & HTML Updates

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/static/style.css` (`:root` block, `body` rule)

**Interfaces:**
- Produces: new CSS tokens consumed by all subsequent tasks; Inter font loaded globally

- [ ] **Step 1: Add Inter font to `index.html` `<head>`**

Replace the existing `<head>` content (keep existing tags, add font links before the stylesheet):

```html
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Job Seeker</title>
  <link rel="icon" type="image/svg+xml" href="/static/favicon.svg" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="/static/style.css" />
</head>
```

- [ ] **Step 2: Update logo markup — remove emoji icon, remove tagline**

Find this block in `index.html`:
```html
    <div class="header-inner">
      <div class="logo">
        <span class="logo-icon">&#128269;</span>
        <span>Job Seeker</span>
      </div>
      <div class="tagline">AI-powered remote job search</div>
    </div>
```

Replace with:
```html
    <div class="header-inner">
      <div class="logo">Job Seeker</div>
    </div>
```

- [ ] **Step 3: Update CV loaded state — remove char count, add green dot**

Find this in `index.html`:
```html
        <span class="cv-status-ok">&#10003; CV loaded (<span id="cv-chars">0</span> chars)</span>
```

Replace with:
```html
        <span class="cv-status-ok">● CV loaded</span>
```

- [ ] **Step 4: Replace `:root` and `body` in `style.css`**

Replace the entire `:root` block and `body` rule (lines 1–26):

```css
/* ===== Reset & Base ===== */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg: #09090b;
  --surface: #111113;
  --border: #27272a;
  --accent: #3b82f6;
  --accent-hover: #2563eb;
  --green: #22c55e;
  --yellow: #f59e0b;
  --red: #ef4444;
  --text: #fafafa;
  --text-muted: #71717a;
  --radius: 10px;
  --radius-sm: 6px;
}

body {
  background: var(--bg);
  color: var(--text);
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  min-height: 100vh;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}
```

- [ ] **Step 5: Verify in browser**

Open `http://localhost:8000` (hard refresh: `Ctrl+Shift+R`).

Expected:
- Background is near-black (`#09090b`) — slightly different from the old `#0f1117`
- Font is Inter (check DevTools → Computed → font-family)
- Header shows `Job Seeker` text only, no magnifier emoji
- No tagline in header

- [ ] **Step 6: Commit**

```bash
git add frontend/index.html frontend/static/style.css
git commit -m "feat: add Inter font, update tokens to neutral dark palette"
```

---

### Task 2: Header, CV Bar & Search

**Files:**
- Modify: `frontend/static/style.css` (header, cv-bar, search sections)

**Interfaces:**
- Consumes: `--bg`, `--border`, `--surface`, `--accent`, `--accent-hover`, `--text-muted`, `--radius`, `--radius-sm` from Task 1
- Produces: slim 52px header, merged CV bar, flat search button, borderless quick chips

- [ ] **Step 1: Replace the `header` CSS block**

Find and replace the entire `/* ===== Header ===== */` section:

```css
/* ===== Header ===== */
header {
  background: var(--bg);
  border-bottom: 1px solid var(--border);
  padding: 0 24px;
  height: 52px;
  display: flex;
  align-items: center;
}
.header-inner {
  max-width: 1100px;
  margin: 0 auto;
  width: 100%;
  display: flex;
  align-items: center;
}
.logo {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text);
  letter-spacing: -0.01em;
}
```

- [ ] **Step 2: Replace the `/* ===== CV Upload Bar ===== */` section**

```css
/* ===== CV Upload Bar ===== */
.cv-bar {
  background: var(--bg);
  border-bottom: 1px solid var(--border);
  padding: 8px 24px;
}
.cv-bar-inner {
  max-width: 1100px;
  margin: 0 auto;
}
.cv-upload-area,
.cv-loaded-area {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.cv-bar-label {
  color: var(--text-muted);
  font-size: 0.82rem;
  white-space: nowrap;
}
.cv-file-label {
  position: relative;
  cursor: pointer;
  background: transparent;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 5px 12px;
  font-size: 0.82rem;
  color: var(--text-muted);
  transition: border-color .15s;
}
.cv-file-label:hover { border-color: var(--accent); color: var(--text); }
.cv-file-label input[type="file"] { display: none; }
.cv-upload-btn {
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  padding: 5px 14px;
  font-size: 0.82rem;
  font-weight: 500;
  cursor: pointer;
  transition: background .15s;
}
.cv-upload-btn:not(:disabled):hover { background: var(--accent-hover); }
.cv-upload-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.cv-hint { color: var(--text-muted); font-size: 0.78rem; }
.cv-status-ok { color: var(--green); font-size: 0.85rem; font-weight: 500; }
.cv-remove-btn {
  background: none;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  padding: 3px 10px;
  font-size: 0.78rem;
  cursor: pointer;
  transition: border-color .15s, color .15s;
}
.cv-remove-btn:hover { border-color: var(--red); color: var(--red); }
```

- [ ] **Step 3: Replace the `/* ===== Search ===== */` section**

```css
/* ===== Search ===== */
.search-section { margin-bottom: 28px; }

.search-bar {
  display: flex;
  gap: 8px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 6px;
  transition: border-color .15s;
}
.search-bar:focus-within { border-color: var(--accent); }

.search-bar input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: var(--text);
  font-size: 0.95rem;
  font-family: inherit;
  padding: 6px 10px;
}
.search-bar input::placeholder { color: var(--text-muted); }

.search-bar button {
  background: var(--accent);
  border: none;
  color: #fff;
  padding: 8px 20px;
  border-radius: var(--radius-sm);
  font-size: 0.88rem;
  font-weight: 500;
  font-family: inherit;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: background .15s;
}
.search-bar button:hover { background: var(--accent-hover); }
.search-bar button:disabled { opacity: 0.5; cursor: not-allowed; }

.quick-tags {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}
.tag-label { color: var(--text-muted); font-size: 0.78rem; }
.quick-tag {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text-muted);
  border-radius: 20px;
  padding: 3px 12px;
  font-size: 0.78rem;
  font-family: inherit;
  cursor: pointer;
  transition: border-color .15s, color .15s;
}
.quick-tag:hover { border-color: var(--accent); color: var(--text); }
```

- [ ] **Step 4: Verify in browser**

Hard refresh. Expected:
- Header is a slim dark bar — no visible background difference from page
- CV bar sits flush below header — same background, separated only by the border line
- Search button is flat blue, no gradient, `border-radius: 6px` (sharper corners)
- Quick tag chips have no background fill — just a thin border outline
- Quick tags turn blue-bordered on hover

- [ ] **Step 5: Commit**

```bash
git add frontend/static/style.css
git commit -m "feat: slim header, merged cv bar, flat search and chip styles"
```

---

### Task 3: Job Cards & Two-Column Grid

**Files:**
- Modify: `frontend/static/style.css` (results, job-list, job-card, score-ring sections)

**Interfaces:**
- Consumes: all tokens from Task 1
- Produces: two-column job grid on desktop; cards with glow-outline hover; 56px score ring

- [ ] **Step 1: Replace the `/* ===== Results ===== */` section**

```css
/* ===== Results ===== */
.results-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  font-size: 0.85rem;
  color: var(--text-muted);
}
.sort-row { display: flex; align-items: center; gap: 8px; }
.sort-row select {
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--text);
  border-radius: var(--radius-sm);
  padding: 4px 10px;
  font-size: 0.82rem;
  font-family: inherit;
  cursor: pointer;
}

.job-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}
```

- [ ] **Step 2: Replace the `/* ===== Job Card ===== */` section**

```css
/* ===== Job Card ===== */
.job-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px 24px;
  cursor: pointer;
  transition: border-color .15s, box-shadow .15s;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 12px;
  align-items: start;
}
.job-card:hover {
  border-color: var(--accent);
  box-shadow: 0 0 0 1px var(--accent);
}

.card-left { min-width: 0; }

.card-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.card-company {
  font-size: 0.85rem;
  color: var(--text-muted);
  margin-bottom: 6px;
}
.card-meta {
  font-size: 0.78rem;
  color: var(--text-muted);
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}
.card-meta span { display: flex; align-items: center; gap: 4px; }

.card-tags { display: flex; flex-wrap: wrap; gap: 5px; }
.chip {
  background: transparent;
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 2px 8px;
  font-size: 0.72rem;
  color: var(--text-muted);
}

.card-right { text-align: center; flex-shrink: 0; }

/* ===== Score Ring ===== */
.score-ring {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 1rem;
  border: 2px solid var(--border);
  line-height: 1.1;
}
.score-ring small { font-size: 0.58rem; font-weight: 400; color: var(--text-muted); }
.score-high  { border-color: var(--green);  color: var(--green); }
.score-mid   { border-color: var(--yellow); color: var(--yellow); }
.score-low   { border-color: var(--red);    color: var(--red); }
.score-none  { border-color: var(--border); color: var(--text-muted); font-size: 0.85rem; }

.badge-source {
  background: transparent;
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 1px 6px;
  font-size: 0.7rem;
  color: var(--text-muted);
}
```

- [ ] **Step 3: Update the responsive breakpoint at the bottom of `style.css`**

Find the `@media (max-width: 600px)` block and replace it:

```css
@media (max-width: 768px) {
  .job-list { grid-template-columns: 1fr; }
  .skill-columns { grid-template-columns: 1fr; }
  .modal { padding: 18px; }
  .header-inner { gap: 6px; }
  .job-card { grid-template-columns: 1fr; }
  .card-right { display: flex; justify-content: flex-start; }
}
```

- [ ] **Step 4: Verify in browser**

Search for `data engineer`. Hard refresh first. Expected:
- Jobs display in **two columns** side by side on desktop
- Card hover shows a **blue glow outline** — no card lift/translate
- Company name is grey/muted — not purple
- Tag chips have no background fill, just a thin border
- Score ring is smaller (`56px`), thinner border (`2px`)
- On mobile / narrow window: single column

- [ ] **Step 5: Commit**

```bash
git add frontend/static/style.css
git commit -m "feat: two-column job grid, card glow hover, score ring polish"
```

---

### Task 4: Modal Polish

**Files:**
- Modify: `frontend/static/style.css` (modal, modal-header, tabs, match tab, cover letter tab)

**Interfaces:**
- Consumes: all tokens from Task 1
- Produces: stronger backdrop blur, blue accent on match summary, flat blue copy button

- [ ] **Step 1: Replace the `/* ===== Modal ===== */` section**

```css
/* ===== Modal ===== */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: 16px;
  backdrop-filter: blur(8px);
}
.modal {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  width: 100%;
  max-width: 740px;
  max-height: 88vh;
  overflow-y: auto;
  position: relative;
  padding: 28px;
}
.modal-close {
  position: absolute;
  top: 14px; right: 16px;
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 1.4rem;
  cursor: pointer;
  line-height: 1;
  transition: color .15s;
}
.modal-close:hover { color: var(--text); }

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 20px;
  padding-right: 30px;
}
.modal-header h2 { font-size: 1.4rem; font-weight: 600; margin-bottom: 5px; }
.m-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  font-size: 0.85rem;
  color: var(--text-muted);
  margin-bottom: 4px;
}
.m-company { color: var(--text-muted); font-weight: 500; }
.dot { color: var(--border); }
.m-salary { font-size: 0.85rem; color: var(--green); margin-top: 4px; }

.m-score-circle {
  width: 72px; height: 72px;
  border-radius: 50%;
  border: 2px solid var(--border);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
  font-weight: 700;
  flex-shrink: 0;
  line-height: 1.1;
  transition: border-color 0.3s, color 0.3s;
}
.m-score-circle small { font-size: 0.6rem; font-weight: 400; color: var(--text-muted); }
.score-scoring {
  border-color: var(--accent) !important;
  color: var(--accent) !important;
  animation: pulse-ring 1.4s ease-in-out infinite;
}
@keyframes pulse-ring {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
```

- [ ] **Step 2: Replace the `/* ===== Tabs ===== */` section**

```css
/* ===== Tabs ===== */
.modal-tabs {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 20px;
}
.tab-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  padding: 8px 16px;
  cursor: pointer;
  font-size: 0.88rem;
  font-family: inherit;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  transition: color .15s;
}
.tab-btn:hover { color: var(--text); }
.tab-btn.active { color: var(--text); border-bottom-color: var(--accent); }
```

- [ ] **Step 3: Replace the overview, match and cover letter tab CSS sections**

Replace from `/* ===== Overview tab ===== */` through to the end of `/* ===== Cover Letter tab ===== */`:

```css
/* ===== Overview tab ===== */
.tag-row { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 16px; }

.description-box {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 16px;
  font-size: 0.87rem;
  color: var(--text-muted);
  white-space: pre-wrap;
  max-height: 280px;
  overflow-y: auto;
  line-height: 1.7;
  margin-bottom: 16px;
}

.apply-btn {
  display: inline-block;
  background: var(--accent);
  color: #fff;
  text-decoration: none;
  padding: 9px 22px;
  border-radius: var(--radius-sm);
  font-weight: 500;
  font-size: 0.88rem;
  transition: background .15s;
}
.apply-btn:hover { background: var(--accent-hover); }

/* ===== Match tab ===== */
.match-summary {
  background: var(--bg);
  border-left: 3px solid var(--accent);
  padding: 12px 16px;
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  font-size: 0.88rem;
  color: var(--text-muted);
  margin-bottom: 20px;
  line-height: 1.7;
}
.skill-columns { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.skill-heading {
  font-size: 0.8rem;
  font-weight: 600;
  margin-bottom: 10px;
  text-transform: uppercase;
  letter-spacing: .06em;
}
.skill-heading.matched { color: var(--green); }
.skill-heading.missing  { color: var(--yellow); }
.skill-list { list-style: none; display: flex; flex-direction: column; gap: 5px; }
.skill-list li {
  background: transparent;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 4px 10px;
  font-size: 0.82rem;
  color: var(--text-muted);
}

/* ===== Cover Letter tab ===== */
.cover-hint {
  color: var(--text-muted);
  font-size: 0.88rem;
  margin-bottom: 14px;
}
.gen-cover-btn {
  background: var(--accent);
  border: none;
  color: #fff;
  padding: 9px 22px;
  border-radius: var(--radius-sm);
  font-size: 0.88rem;
  font-weight: 500;
  font-family: inherit;
  cursor: pointer;
  transition: background .15s;
}
.gen-cover-btn:hover { background: var(--accent-hover); }

.cover-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 40px 0;
  color: var(--text-muted);
}
.cover-loading .spinner { width: 26px; height: 26px; border-width: 2px; }

.cover-output textarea {
  width: 100%;
  height: 280px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
  padding: 16px;
  font-size: 0.87rem;
  line-height: 1.7;
  resize: vertical;
  font-family: inherit;
  margin-bottom: 12px;
}
.cover-actions { display: flex; gap: 10px; }
.copy-btn {
  background: var(--accent);
  border: none;
  color: #fff;
  padding: 8px 18px;
  border-radius: var(--radius-sm);
  font-size: 0.85rem;
  font-weight: 500;
  font-family: inherit;
  cursor: pointer;
  transition: background .15s;
}
.copy-btn:hover { background: var(--accent-hover); }
.regen-btn {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text-muted);
  padding: 8px 18px;
  border-radius: var(--radius-sm);
  font-size: 0.85rem;
  font-family: inherit;
  cursor: pointer;
  transition: border-color .15s, color .15s;
}
.regen-btn:hover { border-color: var(--accent); color: var(--text); }
```

- [ ] **Step 4: Replace the `/* ===== Empty / loading ===== */` and `/* ===== Spinner ===== */` sections**

```css
/* ===== Empty / loading ===== */
.empty-state {
  text-align: center;
  padding: 80px 0;
  color: var(--text-muted);
}
.empty-icon { font-size: 2.4rem; margin-bottom: 12px; }

.hidden { display: none !important; }

/* ===== Spinner ===== */
.spinner {
  width: 16px; height: 16px;
  border: 2px solid rgba(255,255,255,0.2);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin .7s linear infinite;
  display: inline-block;
}
@keyframes spin { to { transform: rotate(360deg); } }
```

- [ ] **Step 5: Replace the `/* ===== Scrollbar ===== */` section**

```css
/* ===== Scrollbar ===== */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }
```

- [ ] **Step 6: Verify in browser**

Open a job card modal. Hard refresh first. Expected:
- Backdrop is dark with visible blur effect
- Modal header title is larger (`1.4rem`)
- Company / location is grey muted text, not purple
- Score circle is `72px`, thin `2px` border
- Active tab has blue underline, inactive tabs are grey
- Match tab summary has a **blue** left border (not purple)
- Skill chips have no background fill
- Cover letter copy button is **blue** (matching search button)
- Regenerate button is outline-style, no fill

- [ ] **Step 7: Commit**

```bash
git add frontend/static/style.css
git commit -m "feat: modal polish — stronger blur, blue accents, flat buttons"
```

---

## Final smoke test

After all 4 tasks:

- [ ] Hard refresh — no layout shift or flash of unstyled content
- [ ] Search returns results — two-column grid on desktop
- [ ] Hover a card — blue glow outline (no lift)
- [ ] Click a card — modal opens with blur backdrop
- [ ] Switch tabs in modal — active tab shows blue underline
- [ ] Generate cover letter — spinner shows, output appears with blue copy button
- [ ] Resize window to < 768px — grid collapses to single column
