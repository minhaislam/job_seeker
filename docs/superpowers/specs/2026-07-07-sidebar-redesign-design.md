---
name: sidebar-redesign
description: Replace the two stacked top bars (logo header + CV bar) with a persistent left sidebar holding CV status and AI provider settings, plus a clearer unscored job-card state
metadata:
  type: project
---

# Sidebar Redesign Design

**Date:** 2026-07-07
**Status:** Approved

---

## Summary

The current layout (from the 2026-07-05 Vercel/Linear-style redesign) stacks a thin logo header and a CV-upload bar above the search/results content. Feedback: the page feels empty, and the LLM settings gear icon (added by the bring-your-own-key feature) doesn't make clear whether the active provider is the app default or a user-chosen override.

This redesign consolidates the header and CV bar into a single persistent left sidebar (~240px) that holds the logo, CV status, and an unambiguous AI Provider status line. The sidebar reuses the existing CV-upload markup/logic and the existing LLM settings modal as-is — only their container and trigger location change. Separately, the unscored job-card state ("?" in a solid ring) is replaced with a muted dash in a dashed ring, so it reads as an intentional state rather than a placeholder/bug.

No new features, no backend changes, no changes to the settings modal's internals or the CV upload/scoring logic.

---

## Sidebar Structure

```
┌─────────────┐
│ Job Seeker  │  ← logo, same text style as today's header logo
│─────────────│
│ YOUR CV     │  ← section label (uppercase, muted, 0.72rem)
│ ● CV loaded │  ← existing cv-loaded-area markup, reused as-is
│ [Remove]    │
│  — or —     │
│ [Choose...] │  ← existing cv-upload-area markup, reused as-is
│ [Upload CV] │
│─────────────│
│ AI PROVIDER │  ← section label
│ ● Default   │  ← new status line (see below)
│   (Ollama)  │
│ Change      │  ← link/button, opens existing settings modal
└─────────────┘
```

Fixed width `240px`, `flex-shrink: 0`, background `var(--surface)`, right border `1px solid var(--border)`, internal padding `20px 16px`, sections stacked vertically with `24px` gap. Section labels: `0.72rem`, uppercase, `letter-spacing: 0.04em`, `color: var(--text-muted)` — same visual weight as existing muted labels elsewhere in the app (e.g. `.cv-bar-label`).

### AI Provider status line

Replaces today's gear-icon-only indicator (`#settings-btn` / `#settings-indicator` in the header). New format, always disambiguating default vs. custom:

- `● Default (Ollama)` — when `session["llm_override"]` is unset (mirrors `GET /api/settings` returning `provider: "default"`)
- `● Custom: OpenRouter` — when an override is active, using the existing `PROVIDER_LABELS` map from `app.js` (`Ollama`/`OpenRouter`/`Anthropic`)

Dot color: `var(--green)` in both cases (both are valid, working states) — this isn't a warning, just a status. A `Change` text link below it opens the same `#settings-modal-overlay` already built; no changes to the modal's HTML, CSS, or JS logic — only the element that triggers `.classList.remove('hidden')` moves from the header gear button to this new sidebar link.

---

## Removed / Consolidated

- `<header>` (logo bar) — removed. Logo text moves into the sidebar top.
- `<div id="cv-bar">` — removed. Its two inner states (`#cv-upload-area`, `#cv-loaded-area`) move into the sidebar's CV section, markup unchanged (same element IDs, same JS event bindings in `app.js` — `cvFileInput`, `cvUploadBtn`, `cvRemoveBtn`, etc. all keep working with no logic changes).
- `#settings-btn` (header gear button) — removed. Replaced by the sidebar's AI Provider section (status line + `Change` link), which opens the same `#settings-modal-overlay`.

## Main Content Area

```css
body { display: flex; min-height: 100vh; }

.main-content { flex: 1; min-width: 0; }
.main-content-inner { max-width: 1100px; margin: 0 auto; padding: 32px 24px; }
```

`<main>` keeps its existing children (search bar, quick tags, results section, empty state) unchanged — it just moves inside `.main-content-inner`, and the outer `.main-content` sits to the right of `.sidebar` in the flex row. No changes to the job grid, search bar, or modal beyond this repositioning.

---

## Responsive Behavior

Below the existing `768px` breakpoint (where the job grid already collapses to one column):

```css
@media (max-width: 768px) {
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

This mirrors how the current CV bar already behaves on mobile — a horizontal strip above the content — just now carrying both CV status and AI provider status in one row instead of two stacked bars.

---

## Unscored Job-Card State

Current (`frontend/static/style.css:221`): `.score-none { border-color: var(--border); color: var(--text-muted); font-size: 0.85rem; }`, rendered with a literal `?` character (`frontend/static/app.js:171`).

Change:
- CSS: add `border-style: dashed;` to `.score-none` — signals "not yet available" rather than reusing the same solid-ring language as a real 0-100% score.
- JS: `frontend/static/app.js:171` — replace the `?` character with `–` (en dash), matching the character already used for the equivalent "no score" state inside the job-detail modal (`_setScore`, `frontend/static/app.js:282`, which already renders `–` for `score == null`). This makes the card and modal consistent.
- `title="Click to score"` tooltip stays unchanged.

---

## Files Changed

| File | Change |
|---|---|
| `frontend/index.html` | Replace `<header>` + `#cv-bar` with a `.sidebar` container (logo, CV section reusing existing markup, new AI Provider section); wrap `<main>` in `.main-content`/`.main-content-inner`; move the settings-modal trigger from `#settings-btn` to a new sidebar element (e.g. `#sidebar-settings-change`); settings modal markup itself (`#settings-modal-overlay` and everything inside) is unchanged |
| `frontend/static/style.css` | Add `.sidebar`, `.sidebar-logo`, `.sidebar-section`, `.sidebar-section-label`, `.main-content`, `.main-content-inner` rules; add the `body { display:flex }` wrapper and the `@media (max-width:768px)` sidebar-collapse rule; remove now-unused `header`/`.header-inner`/`.logo`/`.cv-bar`/`.cv-bar-inner` rules (superseded by sidebar equivalents); add `border-style: dashed` to `.score-none` |
| `frontend/static/app.js` | Retarget the settings-modal-open click listener from `#settings-btn` to the new sidebar trigger element; update `updateSettingsIndicator()` to render the new "Default (Ollama)" / "Custom: OpenRouter" format instead of just the provider label; change the unscored job-card `?` to `–` (`buildCard()`); no other logic changes — CV upload, scoring, cover-letter, and settings save/load flows are untouched |

---

## Out of Scope

- Filters sidebar (source/salary/tags/date) — not part of this round, sidebar only holds CV + AI Provider per the approved scope
- Saved/applied jobs tracker — new functionality, not requested for this round
- Job card visual redesign beyond the unscored-state fix (no new icons, no per-source accent colors) — deferred
- Settings modal internal redesign — modal markup/CSS/JS from the bring-your-own-key feature stays exactly as built, only its trigger moves
- Light theme, animation overhaul — same exclusions as the original 2026-07-05 redesign, still out of scope
- Sidebar collapse/expand toggle on desktop — sidebar is always visible on desktop widths
