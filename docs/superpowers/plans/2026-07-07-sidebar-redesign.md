# Sidebar Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the two stacked top bars (logo header + CV bar) with a persistent left sidebar holding CV status and an unambiguous AI-provider status line, and make the unscored job-card state read as intentional rather than broken.

**Architecture:** Pure frontend restructuring — `body` becomes a flex row with `.sidebar` (fixed 240px) and `.main-content` (flex: 1) as its two children. The sidebar reuses the CV-upload markup and the LLM settings modal exactly as they exist today; only their container and the settings trigger's visual treatment change — element IDs `cv-file-input`, `cv-upload-btn`, `cv-upload-area`, `cv-loaded-area`, `cv-remove-btn`, `settings-btn`, `settings-indicator`, and the entire `#settings-modal-overlay` subtree are preserved unchanged, so `app.js`'s existing event listeners keep working with zero retargeting.

**Tech Stack:** Vanilla HTML/CSS/JS (existing frontend, no new dependencies, no backend changes)

## Global Constraints

- No backend changes. No changes to `backend/` at all.
- No changes to the settings modal's internal markup/CSS/JS (`#settings-modal-overlay` and everything inside it) — only its trigger button's location/class changes.
- No changes to CV upload/scoring logic in `app.js` — only the HTML container around the existing CV elements moves; the element IDs stay identical so no JS diff is needed for CV behavior.
- Sidebar fixed width `240px` on desktop; collapses to a horizontal bar (matching the current CV-bar mobile behavior) below the existing `768px` breakpoint.
- Reuse existing CSS custom properties only (`--bg`, `--surface`, `--border`, `--accent`, `--accent-hover`, `--green`, `--yellow`, `--red`, `--text`, `--text-muted`, `--radius`, `--radius-sm`) — no new color values.
- The design spec (`docs/superpowers/specs/2026-07-07-sidebar-redesign-design.md`) describes wrapping `<main>` in both `.main-content` and `.main-content-inner`. This plan simplifies that to a single `.main-content` wrapper: the pre-existing `main { max-width: 1100px; margin: 0 auto; padding: 32px 24px; }` rule already does exactly what `.main-content-inner` would have done, so adding a second wrapper class would be redundant. This is intentional, not a missed requirement.
- This project has no automated test suite (no pytest, no JS test runner) — verification is manual: grep-based presence checks, a Python-based brace-balance check for JS (no `node` available in this environment), and live-server `curl` checks.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `frontend/index.html` | Modify | Replace `<header>` + `#cv-bar` with `<aside class="sidebar">`; wrap `<main>` in `.main-content` |
| `frontend/static/style.css` | Modify | Add sidebar/main-content styles + mobile collapse; remove now-unused header/cv-bar rules; restyle the settings trigger for its new sidebar location; add dashed border to `.score-none` |
| `frontend/static/app.js` | Modify | `updateSettingsIndicator()` renders "Default (Ollama)" / "Custom: OpenRouter" instead of just the bare provider name; unscored job-card marker changes from `?` to `–` |

**Files unchanged:** everything under `backend/`, `frontend/static/favicon.svg`, all other `app.js` logic (CV upload, search, modal, cover letter, settings save/load — only the two lines named above change)

---

### Task 1: Sidebar markup and styling

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/static/style.css`

**Interfaces:**
- Preserves these element IDs unchanged (Task 2 and existing `app.js` code depend on them): `cv-file-input`, `cv-upload-btn`, `cv-upload-area`, `cv-loaded-area`, `cv-upload-hint`, `cv-remove-btn`, `settings-btn`, `settings-indicator`, and every ID inside `#settings-modal-overlay` (`settings-modal-close`, `settings-provider`, `settings-fields-ollama`, `settings-fields-openrouter`, `settings-fields-anthropic`, `settings-ollama-url`, `settings-ollama-model`, `settings-openrouter-key`, `settings-openrouter-model`, `settings-anthropic-key`, `settings-anthropic-model`, `settings-status`, `settings-save-btn`, `settings-spinner`)
- Produces new CSS classes consumed by nothing else yet: `.sidebar`, `.sidebar-logo`, `.sidebar-section`, `.sidebar-section-label`, `.main-content`, `.sidebar-settings-change`

- [ ] **Step 1: Replace the header/CV-bar block in `frontend/index.html`**

Find (lines 13-42 in the current file):

```html
<body>
  <header>
    <div class="header-inner">
      <div class="logo">Job Seeker</div>
      <button id="settings-btn" class="settings-btn" title="LLM provider settings" aria-label="LLM provider settings">
        &#9881; <span id="settings-indicator" class="settings-indicator">Default</span>
      </button>
    </div>
  </header>

  <div id="cv-bar" class="cv-bar">
    <div class="cv-bar-inner">
      <div id="cv-upload-area" class="cv-upload-area">
        <span class="cv-bar-label">&#128196; Your CV:</span>
        <label class="cv-file-label">
          <input type="file" id="cv-file-input" accept=".pdf,.txt" />
          Choose PDF or TXT
        </label>
        <button id="cv-upload-btn" class="cv-upload-btn" disabled>Upload CV</button>
        <span id="cv-upload-hint" class="cv-hint">Upload your CV to enable job matching</span>
      </div>
      <div id="cv-loaded-area" class="cv-loaded-area hidden">
        <span class="cv-bar-label">&#128196; Your CV:</span>
        <span class="cv-status-ok">● CV loaded</span>
        <button id="cv-remove-btn" class="cv-remove-btn">Remove</button>
      </div>
    </div>
  </div>

  <main>
```

Replace with:

```html
<body>
  <aside class="sidebar">
    <div class="sidebar-logo">Job Seeker</div>

    <div class="sidebar-section">
      <span class="sidebar-section-label">Your CV</span>
      <div id="cv-upload-area" class="cv-upload-area">
        <label class="cv-file-label">
          <input type="file" id="cv-file-input" accept=".pdf,.txt" />
          Choose PDF or TXT
        </label>
        <button id="cv-upload-btn" class="cv-upload-btn" disabled>Upload CV</button>
        <span id="cv-upload-hint" class="cv-hint">Upload your CV to enable job matching</span>
      </div>
      <div id="cv-loaded-area" class="cv-loaded-area hidden">
        <span class="cv-status-ok">● CV loaded</span>
        <button id="cv-remove-btn" class="cv-remove-btn">Remove</button>
      </div>
    </div>

    <div class="sidebar-section">
      <span class="sidebar-section-label">AI Provider</span>
      <span id="settings-indicator" class="settings-indicator">Default</span>
      <button id="settings-btn" class="sidebar-settings-change" title="LLM provider settings" aria-label="LLM provider settings">Change</button>
    </div>
  </aside>

  <div class="main-content">
  <main>
```

> Note: `settings-btn` and `settings-indicator` keep their exact IDs — only their tag content, class, and parent container change. `app.js`'s existing `document.getElementById('settings-btn')` / `document.getElementById('settings-indicator')` calls need no changes.

- [ ] **Step 2: Close the new `.main-content` wrapper around `<main>`**

Find:

```html
    </div>
  </main>

  <!-- Job Detail Modal -->
```

Replace with:

```html
    </div>
  </main>
  </div>

  <!-- Job Detail Modal -->
```

> The two modals (`#modal-overlay`, `#settings-modal-overlay`) stay as direct `<body>` children after this closing `</div>` — both use `position: fixed` (via `.modal-overlay`), so their position in the flex flow doesn't matter.

- [ ] **Step 3: Replace the Header/Main CSS block in `frontend/static/style.css`**

Find (lines 28-53 in the current file):

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
  justify-content: space-between;
}
.logo {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text);
  letter-spacing: -0.01em;
}

/* ===== Main ===== */
main { max-width: 1100px; margin: 0 auto; padding: 32px 24px; }
```

Replace with:

```css
/* ===== Layout Shell ===== */
body { display: flex; min-height: 100vh; }

/* ===== Sidebar ===== */
.sidebar {
  width: 240px;
  flex-shrink: 0;
  background: var(--surface);
  border-right: 1px solid var(--border);
  padding: 20px 16px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}
.sidebar-logo {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text);
  letter-spacing: -0.01em;
}
.sidebar-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.sidebar-section-label {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
}

/* ===== Main ===== */
.main-content { flex: 1; min-width: 0; }
main { max-width: 1100px; margin: 0 auto; padding: 32px 24px; }
```

- [ ] **Step 4: Restyle `.cv-upload-area`/`.cv-loaded-area` for the narrower sidebar and remove the now-unused `.cv-bar`/`.cv-bar-inner`/`.cv-bar-label` rules**

Find (in the `/* ===== CV Upload Bar ===== */` block):

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
```

Replace with:

```css
/* ===== CV Section (sidebar) ===== */
.cv-upload-area,
.cv-loaded-area {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
}
```

- [ ] **Step 5: Restyle the settings trigger for the sidebar (replace `.settings-btn`/`.settings-indicator`)**

Find:

```css
/* ===== Settings ===== */
.settings-btn {
  background: none;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  padding: 4px 10px;
  font-size: 0.95rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: border-color .15s, color .15s;
}
.settings-btn:hover { border-color: var(--accent); color: var(--text); }
.settings-indicator { font-size: 0.75rem; }
```

Replace with:

```css
/* ===== Settings ===== */
.settings-indicator {
  color: var(--green);
  font-size: 0.85rem;
  font-weight: 500;
}
.sidebar-settings-change {
  align-self: flex-start;
  background: none;
  border: none;
  color: var(--accent);
  font-size: 0.78rem;
  padding: 0;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
}
.sidebar-settings-change:hover { color: var(--accent-hover); }
```

> The rest of the `/* ===== Settings ===== */` block (`.settings-modal`, `.settings-desc`, `.settings-field`, `.settings-status`, `.settings-actions`, etc. — everything styling the modal's interior) stays exactly as-is, immediately below what you just replaced. Don't touch those rules.

- [ ] **Step 6: Add the dashed border to the unscored score ring**

Find:

```css
.score-none  { border-color: var(--border); color: var(--text-muted); font-size: 0.85rem; }
```

Replace with:

```css
.score-none  { border-color: var(--border); border-style: dashed; color: var(--text-muted); font-size: 0.85rem; }
```

- [ ] **Step 7: Add the mobile sidebar-collapse rule and remove the stale `.header-inner` mobile rule**

Find (in the `@media (max-width: 768px)` block at the end of the file):

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

Replace with:

```css
@media (max-width: 768px) {
  .job-list { grid-template-columns: 1fr; }
  .skill-columns { grid-template-columns: 1fr; }
  .modal { padding: 18px; }
  .job-card { grid-template-columns: 1fr; }
  .card-right { display: flex; justify-content: flex-start; }

  body { flex-direction: column; }
  .sidebar {
    width: 100%;
    flex-direction: row;
    flex-wrap: wrap;
    align-items: center;
    border-right: none;
    border-bottom: 1px solid var(--border);
    gap: 16px;
    padding: 10px 16px;
  }
  .sidebar-section { flex-direction: row; align-items: center; gap: 8px; }
}
```

- [ ] **Step 8: Verify the old classes are gone and the new ones are present**

```powershell
Select-String -Path frontend/index.html -Pattern "<header>","cv-bar-label","class=""settings-btn""" -Quiet
Select-String -Path frontend/index.html -Pattern "class=""sidebar""","sidebar-section-label","sidebar-settings-change" | Measure-Object | Select-Object -ExpandProperty Count
Select-String -Path frontend/static/style.css -Pattern "^header \{","\.cv-bar \{","\.header-inner" -Quiet
Select-String -Path frontend/static/style.css -Pattern "\.sidebar \{","\.sidebar-settings-change","border-style: dashed" | Measure-Object | Select-Object -ExpandProperty Count
```

Expected: the first and third commands print `False` (`-Quiet` returns a boolean — `False` means no match, which is correct: those old selectors must no longer exist). The second and fourth print a count of `3` or more (new selectors present).

- [ ] **Step 9: Live-server sanity check**

```powershell
$proc = Start-Process -PassThru -NoNewWindow python -ArgumentList "-m","uvicorn","backend.main:app","--port","8020"
Start-Sleep -Seconds 3
Invoke-WebRequest http://localhost:8020/ -UseBasicParsing | Select-Object -ExpandProperty StatusCode
$body = (Invoke-WebRequest http://localhost:8020/ -UseBasicParsing).Content
if ($body -match 'class="sidebar"' -and $body -match 'sidebar-settings-change') { "sidebar markup present: OK" } else { "MISSING sidebar markup" }
Stop-Process -Id $proc.Id -Force
```

Expected: `StatusCode 200`, then `sidebar markup present: OK`.

- [ ] **Step 10: Commit**

```powershell
git add frontend/index.html frontend/static/style.css
git commit -m "feat: restructure header and CV bar into a persistent sidebar"
```

---

### Task 2: Provider-status text and unscored-card marker

**Files:**
- Modify: `frontend/static/app.js`

**Interfaces:**
- Consumes from Task 1: the sidebar markup (no new IDs needed — `settings-indicator` and the job-card score-ring markup are unchanged in structure, only in visual context)
- No new functions or IDs produced — this task only changes the body of two existing functions

- [ ] **Step 1: Update `updateSettingsIndicator()` to disambiguate default vs. custom**

Find (around line 445-449):

```javascript
const PROVIDER_LABELS = { default: 'Default', ollama: 'Ollama', openrouter: 'OpenRouter', anthropic: 'Anthropic' };

function updateSettingsIndicator(provider) {
  settingsIndicator.textContent = PROVIDER_LABELS[provider] || provider;
}
```

Replace with:

```javascript
const PROVIDER_LABELS = { default: 'Default', ollama: 'Ollama', openrouter: 'OpenRouter', anthropic: 'Anthropic' };

function updateSettingsIndicator(provider) {
  const label = PROVIDER_LABELS[provider] || provider;
  settingsIndicator.textContent = provider === 'default'
    ? `● Default (Ollama)`
    : `● Custom: ${label}`;
}
```

> `updateSettingsIndicator` is already called from both `loadSettings()` (page load) and the save success handler — no call-site changes needed.

- [ ] **Step 2: Change the unscored job-card marker from `?` to `–`**

Find (around line 171):

```javascript
    : `<div class="score-ring score-none" title="Click to score">?</div>`;
```

Replace with:

```javascript
    : `<div class="score-ring score-none" title="Click to score">–</div>`;
```

- [ ] **Step 3: Verify JS syntax is still valid**

No `node` is available in this environment. Use a brace-balance sanity check:

```powershell
python -c "
src = open('frontend/static/app.js', encoding='utf-8').read()
depth = 0
for ch in src:
    if ch == '{': depth += 1
    elif ch == '}': depth -= 1
print('brace balance:', depth)
"
```

Expected: `brace balance: 0`

- [ ] **Step 4: Live-server verification of the new indicator text and dash character**

```powershell
$proc = Start-Process -PassThru -NoNewWindow python -ArgumentList "-m","uvicorn","backend.main:app","--port","8020"
Start-Sleep -Seconds 3
$js = (Invoke-WebRequest http://localhost:8020/static/app.js -UseBasicParsing).Content
if ($js -match [regex]::Escape('● Default (Ollama)') -and $js -match [regex]::Escape('● Custom: ${label}')) { "indicator text OK" } else { "MISSING indicator text" }
if ($js -match [regex]::Escape('score-none" title="Click to score">–<')) { "dash marker OK" } else { "MISSING dash marker" }
Stop-Process -Id $proc.Id -Force
```

Expected: `indicator text OK` and `dash marker OK`. (The served file is the literal template-string source, so the `${label}` substring appears verbatim in the unexecuted JS — that's expected, not a bug.)

- [ ] **Step 5: Commit**

```powershell
git add frontend/static/app.js
git commit -m "feat: disambiguate default/custom LLM provider in sidebar and use a dash for unscored jobs"
```

---

## Post-Implementation Smoke Test

After both tasks are committed:

1. Run `.\run.ps1`, open `http://localhost:8000`, hard refresh (`Ctrl+Shift+R`).
2. Confirm the sidebar renders on the left with "Job Seeker" at top, a "Your CV" section, and an "AI Provider" section showing "● Default (Ollama)" (or whatever provider is actually configured) with a "Change" link.
3. Click "Change" — the existing settings modal should open exactly as before (no visual/behavioral regression there).
4. Upload a CV in the sidebar — should work exactly as before (same upload flow, just relocated).
5. Search for a job — before scoring, unscored cards should show a muted dash in a dashed ring instead of "?".
6. Click a job card, let it score — should work exactly as before.
7. Resize the browser below ~768px width (or open dev tools device toolbar) — the sidebar should collapse to a horizontal bar above the content, matching the old CV-bar's mobile behavior.

If any step looks wrong, check the browser console for JS errors and the server console for backend errors.
