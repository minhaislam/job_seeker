# Job Seeker — Project Overview

A locally-hosted web app that searches remote job listings across multiple platforms, scores each job against a candidate profile using a local LLM (Ollama), and generates tailored cover letters on demand.

Built for: **Md. Minhajul Islam** — Senior Data Engineer seeking remote roles.

---

## How to Run

```bat
# Windows
run.bat

# PowerShell
.\run.ps1
```

App available at: `http://localhost:8000`

**Prerequisites:**
- Python 3.10+
- Ollama running locally with at least one model pulled (`ollama list` to verify)
- Dependencies installed via `pip install -r requirements.txt`

---

## Project Structure

```
job_seeker/
│
├── backend/
│   ├── main.py              # FastAPI app — all routes and request handling
│   ├── config.py            # Environment config + candidate profile (USER_PROFILE)
│   ├── models.py            # Pydantic data models (Job, SearchRequest, CoverLetterRequest)
│   │
│   ├── sources/             # Job data fetchers — one file per platform
│   │   ├── remotive.py      # Remotive API (free, no key, remote-only jobs)
│   │   ├── remoteok.py      # RemoteOK API (free, no key, remote-only jobs)
│   │   └── jsearch.py       # JSearch via RapidAPI (LinkedIn, Indeed — needs API key)
│   │
│   └── services/
│       ├── llm.py           # Unified LLM client (Ollama or Anthropic, config-driven)
│       ├── matcher.py       # Job-to-profile match scoring via LLM (returns 0–100)
│       └── cover_letter.py  # Cover letter generation via LLM
│
├── frontend/
│   ├── index.html           # Single-page app shell — left sidebar (CV status + AI provider) + main content area
│   └── static/
│       ├── style.css        # Dark theme, responsive layout
│       ├── app.js           # All frontend logic (search, render, modal, tabs)
│       └── favicon.svg
│
├── .env                     # Local secrets and config (not committed)
├── .env.example             # Template showing all available settings
├── requirements.txt
├── run.bat                  # Windows launcher
└── run.ps1                  # PowerShell launcher
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Serves the frontend |
| `POST` | `/api/search` | Search jobs; returns list with match scores |
| `GET` | `/api/job/{job_id}` | Fetch a single cached job by ID |
| `POST` | `/api/cover-letter` | Generate a cover letter for a given job |

---

## Configuration (`.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_OLLAMA` | `true` | Use local Ollama instead of Anthropic API |
| `OLLAMA_MODEL` | `gemma4:e4b` | Ollama model name (`ollama list` to see options) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server address |
| `ANTHROPIC_API_KEY` | _(blank)_ | Set this and `USE_OLLAMA=false` to use Claude API |
| `RAPIDAPI_KEY` | _(blank)_ | Enables JSearch source (LinkedIn/Indeed/Glassdoor) |

---

## What It Can Do

- **Multi-platform job search** — queries Remotive and RemoteOK in parallel; JSearch (LinkedIn, Indeed) if a RapidAPI key is provided
- **AI match scoring** — each job receives a 0–100 score based on alignment with the candidate profile in `config.py`
- **Match breakdown** — per job: matched skills, gap skills, 2–3 sentence match summary
- **Cover letter generation** — on-demand, personalised to the specific job and company
- **Sort & filter** — sort results by match score, date posted, or company name
- **Quick-search tags** — pre-set keyword buttons for common search terms
- **In-memory job cache** — jobs scored in one search remain accessible for detail/cover letter calls without re-fetching
- **Runs fully offline** — when using Ollama, no internet required after the initial job fetch
- **LLM-agnostic** — swap between Ollama (local) and Anthropic (cloud) via a single `.env` flag

---

## What It Cannot Do (Current Limitations)

### Data & Sources
- **No persistent storage** — job results live in memory only; restarting the server clears all cached jobs
- **No job deduplication across searches** — running the same search twice adds duplicate entries to the cache
- **Limited platforms** — only Remotive and RemoteOK are active; JSearch (`backend/sources/jsearch.py`) is wired but disabled — the free RapidAPI plan only covers `/job-details` not `/search`; re-enable by upgrading JSearch to a paid plan or swapping in Adzuna API (free, 250 req/month)
- **No pagination** — fetches a fixed number of jobs per source (default 20 each); cannot load more results incrementally
- **Job data quality varies** — descriptions from Remotive/RemoteOK may be HTML-stripped text; some fields (salary, tags) are often missing

### AI Features
- **No batch pre-scoring** — jobs beyond the first 15 in a search are returned without a match score (to avoid overwhelming Ollama)
- **Match quality depends on model** — a 4b/7b local model produces reasonable but not expert-level analysis; larger models yield better results
- **Cover letters are not saved** — closing the modal discards the generated letter; no export to file
- **No feedback loop** — cannot mark jobs as "applied", "rejected", or "saved" to improve future matching

### Infrastructure
- **No authentication** — the app is open on localhost; do not expose it on a public network
- **No background refresh** — job listings are only fetched when a search is triggered; no scheduled or automatic refresh
- **No email or calendar integration** — cannot send applications or set reminders
- **Single user only** — profile is hardcoded in `config.py`; no multi-user support

---

## How to Extend

### Add a new job source
1. Create `backend/sources/yourplatform.py`
2. Implement `async def fetch_jobs(query: str, limit: int) -> List[Job]`
3. Import and call it inside `backend/main.py` in the `asyncio.gather(...)` block

**Adzuna** is the recommended next source (free, 250 searches/month):
- Register at `developer.adzuna.com` → get `app_id` + `app_key`
- Endpoint: `https://api.adzuna.com/v1/api/jobs/gb/search/1?what={query}&app_id=X&app_key=Y`
- Change `gb` to target a specific country (`us`, `au`, `de`, etc.)

### Change the candidate profile
Edit the `USER_PROFILE` string in `backend/config.py`. This is the text sent to the LLM for every match and cover letter request.

### Use a different Ollama model
```
# .env
OLLAMA_MODEL=gemma3:4b    # lighter, faster
OLLAMA_MODEL=gemma4:e4b   # current default — better quality
```

### Switch to Anthropic Claude (cloud)
```
# .env
USE_OLLAMA=false
ANTHROPIC_API_KEY=sk-ant-...
```

### Add persistent storage
Replace the `_job_cache` dict in `backend/main.py` with a SQLite database using `aiosqlite` (already in `requirements.txt`). Add a `jobs` table and migrate reads/writes to async DB calls.

### Add a "saved jobs" feature
1. Add a `saved: bool` field to the `Job` model
2. Add a `POST /api/job/{job_id}/save` endpoint
3. Persist saved state to SQLite (see above)
4. Add a "Saved" filter tab in the frontend

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `fastapi` | Web framework and API server |
| `uvicorn` | ASGI server (runs FastAPI) |
| `httpx` | Async HTTP client (job API calls + Ollama calls) |
| `anthropic` | Anthropic SDK (used only when `USE_OLLAMA=false`) |
| `pydantic` | Data validation and models |
| `python-dotenv` | Loads `.env` file into environment |
| `aiosqlite` | Async SQLite driver (included for future persistence use) |
