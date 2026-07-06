# Usage Stats Tracking — Design

## Purpose

Minhajul wants a personal, persistent record of how he's using the app: how many
times he's visited (from any device), what he searched for, how many jobs he
tried to match against his CV, how many "Apply" links he clicked, and how many
cover letters he generated. Data must survive `docker compose up --build`
(container rebuilds) and only be cleared if he deletes it manually.

This is single-user, personal usage tracking — not public/multi-tenant
analytics, and not gated behind auth (matches the app's existing no-auth,
single-user posture).

## Storage

A single JSON file at `data/stats.json`:

```json
{
  "visits": 12,
  "searches": [
    {"query": "data engineer", "timestamp": "2026-07-06T14:32:10+00:00"}
  ],
  "matches": 42,
  "applies": 7,
  "cover_letters": 5
}
```

- `backend/services/stats.py` owns all reads/writes. Synchronous `json.load`/
  `json.dump` — safe because uvicorn runs single-process/single-worker (the
  same assumption `_sessions`/`_job_cache` in `main.py` already rely on), and
  there is no `await` between reading and writing a record, so two requests
  can never interleave a write.
- Writes go to `data/stats.json.tmp` then `os.replace()` to the real path —
  atomic, so a crash mid-write can't corrupt the file.
- If the file is missing or corrupt, `_load()` returns a fresh default dict
  rather than raising.
- Every `record_*` function catches and logs its own exceptions internally
  (e.g. disk full/permission errors) — a stats-write failure must never break
  search, scoring, or cover-letter generation.
- `data/` is mounted as a Docker volume (`./data:/app/data` in
  `docker-compose.yml`) so the file persists across `--build`. Added to
  `.gitignore`.

## Events recorded

| Event | Hook point | Effect |
|---|---|---|
| Visit | `_get_session()` in `main.py`, only on the branch that creates a brand-new session (no valid cookie yet) | `visits += 1` |
| Search | `POST /api/search`, every call | append `{query, timestamp}` to `searches` |
| Match attempt | `GET /api/job/{id}`, only the first time a job is scored in a session (existing `if score is None` branch) | `matches += 1`, even if the LLM call fails and the code falls back to the default score-50 — an attempt is an attempt |
| Apply click | New. The "Apply Now" link currently just navigates via `target="_blank"` with no backend call | `applies += 1`, via new `POST /api/track/apply` |
| Cover letter | `POST /api/cover-letter`, after a successful `cover_letter.generate()` call | `cover_letters += 1` |

## New API endpoints

- `POST /api/track/apply` — body `{"job_id": str}`. Fire-and-forget from the
  frontend; always returns `{"status": "ok"}`. Records an apply-click.
- `GET /api/stats` — returns:
  ```json
  {
    "visits": 12,
    "searches_count": 34,
    "searches": [{"query": "...", "timestamp": "..."}, ...],
    "matches_count": 42,
    "applies_count": 7,
    "cover_letters_count": 5
  }
  ```
  `searches` is newest-first.

## Frontend

- New route `GET /stats` (registered like the existing `GET /` index route,
  ahead of the catch-all `StaticFiles` mount) serves `frontend/stats.html`.
- `stats.html` matches the existing dark theme and shows:
  - Four stat tiles: Visits, Jobs matched, Applies clicked, Cover letters
    generated (counts only).
  - A "Searches" section: full chronological list (newest first), each row
    showing the query and its timestamp.
  - Fetches `/api/stats` on load via the same vanilla-JS `fetch` pattern used
    throughout `app.js`.
- A small "Stats" link is added to the header next to the logo.
- `app.js`: a click listener on `#m-apply-link` fires
  `fetch('/api/track/apply', {method: 'POST', ..., keepalive: true})`
  without calling `preventDefault()` — the link still navigates normally
  (opens in a new tab via `target="_blank"`), the tracking call is best-effort
  and its failure is silently ignored.

## Error handling

- `stats.py` functions never raise out of `record_*`/`get_stats` — internal
  try/except with a `print(...)` warning on failure, returning safe defaults.
- `/api/track/apply` always returns 200 `{"status": "ok"}` even if the
  underlying write failed, since this is a best-effort tracking beacon, not a
  user-facing feature with error states.

## Testing / verification

No test framework exists in this repo. Verification will be a one-off script
(as used earlier this session for the session-cookie and retry-logic fixes):
start the app, drive the full flow (new session → search → score a job →
hit the apply-tracking endpoint → generate a cover letter), then confirm
`/api/stats` reflects the expected counts and that the counts survive a
process restart (proving the JSON file round-trips correctly).

## Out of scope (YAGNI)

- No auth/access control on `/stats` or `/api/stats`.
- No per-device breakdown beyond the single aggregate visit counter.
- No full history lists for matches/applies/cover-letters (counts only, per
  explicit decision) — only searches get a full list.
- No data export/clearing UI — clearing means manually deleting
  `data/stats.json`.
