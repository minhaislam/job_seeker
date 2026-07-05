---
name: frontend-redesign
description: Redesign the job seeker frontend to a minimal, professional Vercel/Linear-style dark theme with two-column job card grid and Inter typography
metadata:
  type: project
---

# Frontend Redesign Design

**Date:** 2026-07-05
**Goal:** Polish the existing dark-themed single-page app into a minimal, professional tool — Vercel/Linear aesthetic. No framework changes, no structural changes. CSS and HTML tweaks only.

---

## Direction

**Neutral Dark** — near-black background, off-white text, single blue accent. No gradients. No decorative elements. Content and spacing do all the work. Reference: Vercel dashboard, Linear, GitHub dark mode.

---

## Color Palette

| Token | Value | Usage |
|---|---|---|
| `--bg` | `#09090b` | Page background |
| `--surface` | `#111113` | Cards, modals |
| `--border` | `#27272a` | All borders (1px) |
| `--text` | `#fafafa` | Primary text |
| `--text-muted` | `#71717a` | Secondary text, labels |
| `--accent` | `#3b82f6` | Blue — buttons, focus, active states |
| `--accent-hover` | `#2563eb` | Button hover |
| `--green` | `#22c55e` | High match score |
| `--yellow` | `#f59e0b` | Mid match score |
| `--red` | `#ef4444` | Low match score |

Removed: `--surface2`, `--accent-light`. These created too many surface levels.

---

## Typography

- **Font:** `Inter` (Google Fonts) — replaces `Segoe UI`
- Add to `index.html` `<head>`: `<link rel="preconnect" href="https://fonts.googleapis.com">` + Inter 400/500/600 weights
- Single font family throughout — no decorative type
- Base line-height: `1.6` (unchanged)

---

## Header

- Height: `~52px` — slim bar, gets out of the way
- Background: `#09090b` — same as page, no separate color or gradient
- Bottom border: `1px solid #27272a`
- Logo: text only — `Inter 600`, white, no emoji icon. Text: `Job Seeker`
- Tagline: **removed** from header
- No change to max-width container (`1100px`)

---

## CV Bar

- Background: `#09090b` — merges with header visually
- Bottom border: `1px solid #27272a`
- All elements on one row, no wrapping on desktop
- Uploaded state: small green dot (`●`) + `CV loaded` text — no char count displayed
- Remove button: stays, same style

---

## Search Bar

- Container: `background: #111113`, `border: 1px solid #27272a`, `border-radius: 8px`
- Focus: border becomes `#3b82f6`
- Search button: `background: #3b82f6`, `border-radius: 6px` (was `8px`), flat — no gradient
- Button hover: `background: #2563eb`
- Quick tag chips: `border: 1px solid #27272a`, **no background fill**, muted text
- Quick tag hover: `border-color: #3b82f6`, text becomes `#fafafa`

---

## Job Cards — Two-Column Grid

### Layout
```css
.job-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}
@media (max-width: 768px) {
  .job-list { grid-template-columns: 1fr; }
}
```

### Card design
- Background: `#111113`
- Border: `1px solid #27272a`
- Border-radius: `10px`
- Padding: `20px 24px`
- Hover: `border-color: #3b82f6` + `box-shadow: 0 0 0 1px #3b82f6` — **no translateY**
- Transition: `border-color .15s, box-shadow .15s`

### Card content
- Title: `#fafafa`, `font-weight: 600`, `1rem`
- Company: `#71717a` (muted) — was accent-light purple
- Meta row (location, date, source): `#71717a`, `0.82rem`
- Tags: `border: 1px solid #27272a`, no fill, `#71717a` text, `border-radius: 4px`, `padding: 2px 8px`
- Source badge: same tag style, no separate `.badge-source` distinction needed

### Score ring
- Size: `56px × 56px` (was `64px`)
- Border: `2px solid` (was `3px`)
- "Not yet scored" state: `…` in muted color, `font-size: 1rem`

---

## Modal

### Shell
- Background: `#111113`
- Border: `1px solid #27272a`
- Backdrop: `rgba(0,0,0,0.85)` + `backdrop-filter: blur(8px)`
- Border-radius: `12px` (unchanged)
- Max-width: `740px` (unchanged)

### Header
- Title: `1.4rem`, `font-weight: 600`
- Company/location/source: one muted line, `0.85rem`, `#71717a`
- Score circle: `72px`, `2px` border — same color logic (green/yellow/red/blue-accent for scoring)
- Salary: `#22c55e` if present

### Tabs
- Active: `#fafafa` text + `2px solid #3b82f6` bottom border
- Inactive: `#71717a` text, no underline
- Tab bar: `border-bottom: 1px solid #27272a`

### Match tab
- Summary block: `border-left: 3px solid #3b82f6` (blue, was purple)
- Skill chips: same quiet pill style as card tags — `border: 1px solid #27272a`, no fill

### Cover letter tab
- Textarea: `background: #09090b`, `border: 1px solid #27272a`
- Copy button: `background: #3b82f6`, same style as search button
- Regenerate: outline style, `border: 1px solid #27272a`, muted text

---

## Files changed

| File | Change |
|---|---|
| `frontend/index.html` | Add Inter font link, update logo markup (remove emoji), update CV loaded state markup |
| `frontend/static/style.css` | Full token + component restyle per spec above |

No changes to `app.js`, backend, or any other files.

---

## Out of scope

- Light theme variant
- Animation overhaul
- New features or components
- Mobile-specific layout changes beyond the grid breakpoint
