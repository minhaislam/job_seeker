# Design: CV Upload

**Date:** 2026-07-05  
**Status:** Approved

---

## Summary

Replace the hardcoded `USER_PROFILE` / `_PROFILE` constants with a dynamic CV uploaded by the user at runtime. Users upload a PDF or plain text file once per session. Job scoring and cover letter generation use the uploaded text. If no CV is uploaded, clicking a job card shows a prompt instead of a score.

---

## Scope

**Files changed:**
- `backend/main.py` — add `_user_profile` global; add `POST /api/cv` and `GET /api/cv/status` endpoints; pass profile to scorer and cover letter generator
- `backend/services/matcher.py` — `score_job(job, profile)` accepts profile as param; remove hardcoded `_PROFILE`
- `backend/services/cover_letter.py` — `generate(req, profile)` accepts profile as param; remove `USER_PROFILE` import
- `backend/config.py` — remove `USER_PROFILE` constant
- `frontend/index.html` — add CV upload bar; update tagline
- `frontend/static/app.js` — upload logic; block scoring if no CV; show nudge message
- `requirements.txt` — add `pypdf`

**Files unchanged:** `models.py`, all sources, `llm.py`, `config.py` env vars, `.env`

---

## Backend

### New global in `main.py`

```python
_user_profile: str = ""
```

Same pattern as `_job_cache`. Cleared on server restart (in-memory, per-session).

### `POST /api/cv`

- Accepts: `multipart/form-data` with field `file` (PDF or `.txt`)
- PDF: extract text with `pypdf.PdfReader`
- TXT: decode bytes as UTF-8
- Stores result in `_user_profile`
- Returns: `{"status": "ok", "chars": len(_user_profile)}`
- Error: 400 if unsupported file type; 400 if extracted text is empty

### `GET /api/cv/status`

- Returns: `{"uploaded": true}` if `_user_profile` is non-empty, else `{"uploaded": false}`
- Frontend calls this on page load to sync UI state

### `matcher.score_job(job, profile: str)`

Signature changes from `score_job(job: Job)` to `score_job(job: Job, profile: str)`. The `profile` string replaces the hardcoded `_PROFILE`. The prompt template is unchanged — `{_PROFILE}` placeholder becomes `{profile}`.

### `cover_letter.generate(req, profile: str)`

Signature changes from `generate(req: CoverLetterRequest)` to `generate(req: CoverLetterRequest, profile: str)`. Replaces `{USER_PROFILE}` in the prompt with `{profile}`. Removes the `from backend.config import USER_PROFILE` import.

### Callers in `main.py`

```python
# scoring
score_data = await matcher.score_job(job, _user_profile)

# cover letter
text = await cover_letter.generate(req, _user_profile)
```

### `config.py`

Remove `USER_PROFILE` entirely. No other changes.

---

## Frontend

### CV upload bar (`index.html`)

Sits between the `<header>` and `<main>`. Shows one of two states:

**State A — no CV uploaded:**
```
[ Choose PDF or TXT file ]  [ Upload CV ]
```

**State B — CV loaded:**
```
✓ CV loaded (4,312 chars)   [ Remove ]
```

### JS logic (`app.js`)

- On page load: `GET /api/cv/status` → if `uploaded: true`, show State B (in case of hot-reload)
- Upload button click: `POST /api/cv` with FormData → on success, switch to State B
- Remove link click: clears local `cvUploaded` flag, shows State A (no server endpoint needed — profile persists in server memory until restart, but UI shows "not uploaded" so scoring is blocked)
- Job card click (scoring trigger): if `cvUploaded === false`, show inline nudge instead of calling API

### Nudge message (job card)

When a job card is clicked without a CV:

```
Upload your CV above to see match score.
```

Shown in place of the score percentage inside the card. No modal, no blocking of the search or other UI.

### Header tagline

Change from:
> "AI-powered remote job search for Minhajul"

To:
> "AI-powered remote job search"

---

## Dependencies

Add to `requirements.txt`:
```
pypdf
```

No other new dependencies.

---

## Out of Scope

- No `DELETE /api/cv` endpoint — "Remove" just resets the frontend flag; server profile persists until restart
- No CV persistence across browser sessions (in-memory only)
- No file size validation (local app, trusted input)
- No multi-user support
- No DOCX support
