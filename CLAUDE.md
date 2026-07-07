# Job Seeker — CLAUDE.md

Local web app for Minhajul Islam: searches remote jobs across platforms, scores each against his CV using AI, and generates cover letters on demand.

---

## Stack

| Layer | Tech |
|---|---|
| Backend | Python 3.12, FastAPI, uvicorn |
| Frontend | Vanilla HTML/CSS/JS (single page, no framework) |
| AI (local) | Ollama — `gemma4:e4b` by default |
| AI (cloud) | OpenRouter or Anthropic Claude API (toggle via `LLM_PROVIDER` in `.env`) |
| Job sources | Remotive, RemoteOK, JSearch (RapidAPI — LinkedIn/Indeed/Glassdoor) |
| HTTP client | `httpx` (async) |

---

## Running the app

```powershell
.\run.ps1          # PowerShell
run.bat            # CMD
```

App runs at `http://localhost:8000`. The server hot-reloads on file changes (uvicorn `--reload`).

**After changing frontend JS/CSS**: do a hard refresh in the browser (`Ctrl+Shift+R`) — uvicorn does not bust browser caches.

---

## Key files

```
backend/
  main.py            — FastAPI routes; lazy job scoring on /api/job/{id}
  config.py          — Env config + USER_PROFILE (Minhajul's CV text)
  models.py          — Pydantic models: Job, SearchRequest, CoverLetterRequest
  sources/
    remotive.py      — Remotive API (free, no key)
    remoteok.py      — RemoteOK API (free, no key)
    jsearch.py       — JSearch via RapidAPI (LinkedIn/Indeed/Glassdoor)
  services/
    llm.py           — Unified LLM client (Ollama / OpenRouter / Anthropic, config-driven)
    matcher.py       — Job-to-CV match scoring; returns score 0–100 + breakdown
    cover_letter.py  — Cover letter generation

frontend/
  index.html         — Single-page app shell; left sidebar (CV status + AI provider) + main content area
  static/app.js      — All frontend logic (search, cards, modal, lazy scoring)
  static/style.css   — Dark theme
```

---

## Environment variables (`.env`)

`.env` is gitignored — never commit it. Use `.env.example` as the template.

| Variable | Purpose |
|---|---|
| `LLM_PROVIDER` | `ollama` / `openrouter` / `anthropic` (default: `ollama`) |
| `OLLAMA_MODEL` | Model name (`gemma4:e4b`, `gemma3:4b`, etc.) |
| `OLLAMA_BASE_URL` | Ollama server (default `http://localhost:11434`) |
| `OPENROUTER_API_KEY` | Required when `LLM_PROVIDER=openrouter` |
| `OPENROUTER_MODEL` | OpenRouter model string (e.g. `google/gemma-3-4b-it:free`) |
| `ANTHROPIC_API_KEY` | Required when `LLM_PROVIDER=anthropic` |
| `RAPIDAPI_KEY` | Enables JSearch — LinkedIn/Indeed/Glassdoor results |

---

## Architecture decisions

**Lazy scoring** — jobs are fetched immediately on search with no score. Scoring runs only when the user clicks a job card (`GET /api/job/{id}`). This keeps search fast and avoids overwhelming Ollama with concurrent requests.

**Sequential Ollama calls** — Ollama processes one request at a time. Concurrent scoring causes timeouts on large models (9.6GB+). All scoring is sequential by design.

**Relevance filter** — after fetching from all sources, `_is_relevant()` in `main.py` requires all meaningful words in the search query to appear in the job title or tags. This filters out off-topic results (e.g. "Product Engineer" when searching "data engineer").

**LLM prompt design** — `matcher.py` sends a condensed profile (~80 tokens) instead of the full CV to keep small-model attention focused. The prompt includes explicit cloud-transfer rules (GCP ↔ AWS) to prevent `gemma4` from penalising BigQuery experience when a job asks for Redshift.

**Job cache** — `_job_cache` in `main.py` is an in-memory dict keyed by `job.id`. It persists scored results within a session so clicking the same job twice doesn't re-score. Restarting the server clears it.

---

## Candidate profile

Stored in `backend/config.py` as `USER_PROFILE`. Sent to the LLM for every match and cover letter request. Edit this string to update the CV.

Key facts about Minhajul:
- Senior Data Engineer, 5+ years, based in Dhaka (remote-only)
- Expert: Python, SQL, BigQuery, Airflow v3, DBT, Docker
- Cloud: GCP (primary), AWS (S3, EC2, RDS)
- Seeking: remote Senior/Staff Data Engineer roles

---

## Adding a new job source

1. Create `backend/sources/yourplatform.py`
2. Implement `async def fetch_jobs(query: str, limit: int) -> List[Job]`
3. Import and add it to the `asyncio.gather(...)` call in `backend/main.py`

---

## Common issues

| Symptom | Cause | Fix |
|---|---|---|
| Matcher returns 0% for good jobs | Small Ollama model (gemma4:e4b) lacks reasoning quality | Switch to `LLM_PROVIDER=openrouter` or `LLM_PROVIDER=anthropic` |
| Scoring takes 30–60s | Ollama processing large model | Expected; use `gemma3:4b` for speed |
| JSearch returns 0 jobs | Invalid/missing `RAPIDAPI_KEY` | Check `.env` and RapidAPI subscription |
| Old JS behaviour after code change | Browser cache | Hard refresh: `Ctrl+Shift+R` |
| 500 on search | Usually a source API error | Check server console for `[Remotive]`, `[RemoteOK]`, `[JSearch]` error lines |
| `ValueError: Unknown LLM_PROVIDER` | Typo or old `USE_OLLAMA` in `.env` | Set `LLM_PROVIDER=ollama`, `openrouter`, or `anthropic` |
| OpenRouter 401 on scoring/cover letter | Missing/invalid `OPENROUTER_API_KEY` | Check `.env` and openrouter.ai dashboard |
| OpenRouter 404 on model | Invalid `OPENROUTER_MODEL` string | Check model ID at openrouter.ai/models |
