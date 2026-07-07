# Bring-Your-Own LLM Key Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let each browser session override the app's default LLM provider (Ollama / OpenRouter / Anthropic) with its own key/URL/model, validated live before saving, stored only in the existing in-memory session — no accounts, no database.

**Architecture:** `llm.chat()` gains an optional `override` dict that wins field-by-field over the `.env` defaults already in `backend/config.py`. `matcher.py` and `cover_letter.py` thread `override` through to `chat()`. `main.py` stores the override in the same cookie-keyed session dict that already holds the uploaded CV, exposes it via `GET`/`POST /api/settings` (POST validates with one live call before persisting), and passes `session["llm_override"]` into the three existing LLM call sites. A gear icon in the header opens a modal (frontend-only, no new page) to edit it.

**Tech Stack:** Python 3.12, FastAPI, httpx (existing), Pydantic, vanilla JS/CSS (existing frontend, no new dependencies)

## Global Constraints

- No new pip dependencies.
- `chat()`'s existing signature `chat(prompt: str, json_mode: bool = False)` must remain valid — `override` is an additional optional parameter, not a breaking change.
- `RAPIDAPI_KEY` / job-source config stays server-only — this feature only touches the LLM providers.
- Settings persist only in the server-side session dict (same lifetime as the uploaded CV) — no localStorage, no cross-restart persistence.
- A saved override must never be echoed back to the browser in plaintext (`GET /api/settings` returns `has_api_key: bool`, never the key itself).
- Provider validation errors returned to the browser must be short, mapped messages (`"Invalid API key"`, etc.) — never raw exception text, which could carry request/header details.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `backend/models.py` | Modify | Add `LLMSettings` request model |
| `backend/services/llm.py` | Modify | `chat()` accepts `override`; resolve provider/key/url/model per-call; provider functions take explicit params instead of reading module constants |
| `backend/services/matcher.py` | Modify | `score_job` and `suggest_queries` accept and forward `override` |
| `backend/services/cover_letter.py` | Modify | `generate` accepts and forwards `override` |
| `backend/main.py` | Modify | Session gains `llm_override`; add `GET`/`POST /api/settings`; wire `override` into the three call sites |
| `frontend/index.html` | Modify | Gear icon in header; new settings modal markup |
| `frontend/static/style.css` | Modify | Styles for gear icon, indicator, settings modal fields |
| `frontend/static/app.js` | Modify | Settings modal open/close, provider field toggling, load/save against `/api/settings` |

**Files unchanged:** `backend/config.py`, `backend/sources/*`, `.env` / `.env.example`

---

### Task 1: `llm.py` override resolution + `LLMSettings` model

**Files:**
- Modify: `backend/models.py`
- Modify: `backend/services/llm.py`

**Interfaces:**
- Produces: `LLMSettings` Pydantic model in `backend.models` (`provider: str`, `api_key: Optional[str]`, `base_url: Optional[str]`, `model: Optional[str]`) — consumed by Task 3 (`main.py` endpoint body) and Task 4/5 (frontend JSON shape)
- Produces: `chat(prompt: str, json_mode: bool = False, override: dict | None = None) -> str` — consumed by Task 2 (`matcher.py`, `cover_letter.py`)
- `override` dict shape (plain dict, not the Pydantic model — callers pass `session["llm_override"]` or `None`): `{"provider": str, "api_key": str | None, "base_url": str | None, "model": str | None}`

- [ ] **Step 1: Add `LLMSettings` to `backend/models.py`**

Add this class at the end of the file:

```python
class LLMSettings(BaseModel):
    provider: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
```

- [ ] **Step 2: Rewrite `backend/services/llm.py`**

Replace the entire file content:

```python
"""
Unified LLM client.
Controlled via .env:
  LLM_PROVIDER=ollama       + OLLAMA_MODEL=...          → local Ollama
  LLM_PROVIDER=openrouter   + OPENROUTER_API_KEY=...    → OpenRouter cloud
  LLM_PROVIDER=anthropic    + ANTHROPIC_API_KEY=...     → Anthropic direct

Any call to chat() may pass `override` — a plain dict shaped like
backend.models.LLMSettings (provider/api_key/base_url/model) — to use a
different provider/key/model/base_url for that call only, without
touching the server-wide .env defaults. Fields left blank/None in the
override fall back to the matching .env value.
"""

import asyncio
import json
import httpx
from backend.config import (
    ANTHROPIC_API_KEY,
    LLM_PROVIDER,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OPENROUTER_API_KEY,
    OPENROUTER_MODEL,
)

ANTHROPIC_DEFAULT_MODEL = "claude-sonnet-4-6"

# Fail fast at startup if required keys are missing for the server's own default provider
if LLM_PROVIDER == "openrouter":
    if not OPENROUTER_API_KEY:
        raise ValueError("LLM_PROVIDER=openrouter requires OPENROUTER_API_KEY in .env")
    if not OPENROUTER_MODEL:
        raise ValueError("LLM_PROVIDER=openrouter requires OPENROUTER_MODEL in .env")
elif LLM_PROVIDER == "anthropic":
    if not ANTHROPIC_API_KEY:
        raise ValueError("LLM_PROVIDER=anthropic requires ANTHROPIC_API_KEY in .env")


async def chat(prompt: str, json_mode: bool = False, override: dict | None = None) -> str:
    override = override or {}
    provider = override.get("provider") or LLM_PROVIDER
    if provider == "default":
        provider = LLM_PROVIDER

    if provider == "ollama":
        base_url = override.get("base_url") or OLLAMA_BASE_URL
        model = override.get("model") or OLLAMA_MODEL
        return await _ollama_chat(prompt, json_mode, base_url, model)
    elif provider == "openrouter":
        api_key = override.get("api_key") or OPENROUTER_API_KEY
        model = override.get("model") or OPENROUTER_MODEL
        return await _openrouter_chat(prompt, api_key, model)
    elif provider == "anthropic":
        api_key = override.get("api_key") or ANTHROPIC_API_KEY
        model = override.get("model") or ANTHROPIC_DEFAULT_MODEL
        return await _anthropic_chat(prompt, api_key, model)
    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER: {provider!r}. Use ollama, openrouter, or anthropic."
        )


async def _ollama_chat(prompt: str, json_mode: bool, base_url: str, model: str) -> str:
    payload: dict = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.1},
    }
    if json_mode:
        payload["format"] = "json"

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(f"{base_url}/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["message"]["content"]


async def _openrouter_chat(prompt: str, api_key: str, model: str, max_retries: int = 3) -> str:
    backoff = 1.0
    async with httpx.AsyncClient(timeout=120) as client:
        for attempt in range(max_retries + 1):
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                },
            )
            if resp.status_code == 429 and attempt < max_retries:
                wait = float(resp.headers.get("Retry-After", backoff))
                print(f"[LLM] OpenRouter 429, retrying in {wait:.1f}s (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(wait)
                backoff *= 2
                continue
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]


async def _anthropic_chat(prompt: str, api_key: str, model: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def parse_json_response(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1]
        if text.startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(text[start:end])
        raise
```

> Note: `_openrouter_chat` keeps the `asyncio` retry-on-429 behavior already present in the current file — don't drop it.

- [ ] **Step 3: Verify it imports cleanly**

Run from the project root:

```powershell
python -c "from backend.services.llm import chat; from backend.models import LLMSettings; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Verify unknown-provider override is rejected**

```powershell
python -c "
import asyncio
from backend.services.llm import chat
async def main():
    try:
        await chat('test', override={'provider': 'bogus'})
    except ValueError as e:
        print('GOOD:', e)
asyncio.run(main())
"
```

Expected output: `GOOD: Unknown LLM_PROVIDER: 'bogus'. Use ollama, openrouter, or anthropic.`

- [ ] **Step 5: Verify override fields actually reach the HTTP call**

This proves `base_url` from the override — not the `.env` default — is what gets used, without needing a real Ollama server:

```powershell
python -c "
import asyncio
from backend.services.llm import chat
async def main():
    try:
        await chat('test', override={'provider': 'ollama', 'base_url': 'http://127.0.0.1:1'})
    except Exception as e:
        print('GOOD:', type(e).__name__)
asyncio.run(main())
"
```

Expected output: `GOOD: ConnectError` (connection refused on port 1 — proves the overridden `base_url` was used, not `OLLAMA_BASE_URL`)

- [ ] **Step 6: Commit**

```powershell
git add backend/models.py backend/services/llm.py
git commit -m "feat: add per-call LLM provider override to chat()"
```

---

### Task 2: Thread `override` through `matcher.py` and `cover_letter.py`

**Files:**
- Modify: `backend/services/matcher.py`
- Modify: `backend/services/cover_letter.py`

**Interfaces:**
- Consumes from Task 1: `chat(prompt, json_mode=False, override=None)`
- Produces: `score_job(job: Job, profile: str, override: dict | None = None) -> dict`, `suggest_queries(profile: str, max_suggestions: int = 5, override: dict | None = None) -> list[str]`, `generate(req: CoverLetterRequest, profile: str, override: dict | None = None) -> str` — consumed by Task 3 (`main.py` call sites)

- [ ] **Step 1: Update `backend/services/matcher.py`**

Change the two function signatures and their `chat(...)` calls:

```python
async def suggest_queries(profile: str, max_suggestions: int = 5, override: dict | None = None) -> list[str]:
    prompt = f"""Based on this candidate's CV, suggest up to {max_suggestions} short job-search query strings
they should use to find relevant remote job listings (e.g. "senior data engineer", "BigQuery Airflow", "python ETL remote").
Keep each query 2-5 words, focused on their strongest skills and target role. Reply with ONLY a JSON object, no other text.

CANDIDATE:
{profile}

Return ONLY this JSON:
{{"queries": ["query1", "query2", ...]}}"""

    try:
        text = await chat(prompt, json_mode=True, override=override)
        data = parse_json_response(text)
        queries = data.get("queries", [])
        return [q.strip() for q in queries if isinstance(q, str) and q.strip()][:max_suggestions]
    except Exception as e:
        print(f"[Matcher] suggest_queries error: {type(e).__name__}: {e}")
        return []
```

```python
async def score_job(job: Job, profile: str, override: dict | None = None) -> dict:
    desc = _relevant_description(job.description)
    tags = ", ".join(job.tags) if job.tags else "none listed"

    prompt = f"""Score how well this job fits the candidate. Reply with ONLY a JSON object, no other text.

SCORING RULES:
- Cloud platforms are transferable: GCP=AWS=Azure (BigQuery≈Redshift, GCS≈S3, Datastream≈Glue)
- SQL expertise applies across all databases
- Data engineering experience transfers across industries and cloud providers
- Base score on ability to do the job, not exact keyword matches
- 80-100: Excellent — matches 80%+ requirements at correct seniority
- 60-79: Good — meets core requirements, minor gaps
- 40-59: Partial — solid fundamentals but notable gaps
- 20-39: Poor — major skill or seniority mismatch
- 0-19: Not a fit

CANDIDATE:
{profile}

JOB:
Title: {job.title}
Tags: {tags}
{desc}

Return ONLY this JSON:
{{"score": <integer 0-100>, "summary": "<one concise sentence>", "matched_skills": ["skill1", "skill2"], "missing_skills": ["skill1", "skill2"]}}"""

    try:
        text = await chat(prompt, json_mode=True, override=override)
        return parse_json_response(text)
    except Exception as e:
        print(f"[Matcher] error: {type(e).__name__}: {e}")
        return {
            "score": 50,
            "summary": "Could not score this job.",
            "matched_skills": [],
            "missing_skills": [],
        }
```

Only the function signatures and the `chat(...)` call lines change — prompt text is untouched.

- [ ] **Step 2: Update `backend/services/cover_letter.py`**

```python
from backend.models import CoverLetterRequest
from backend.services.llm import chat


async def generate(req: CoverLetterRequest, profile: str, override: dict | None = None) -> str:
    prompt = f"""Write a professional cover letter for the following job application.

CANDIDATE PROFILE:
{profile}

JOB DETAILS:
Title: {req.job_title}
Company: {req.company}

Job Description (first 1500 chars):
{req.description[:1500]}

Instructions:
- Write a concise, professional cover letter (3-4 paragraphs)
- Open with a strong hook connecting the candidate's most relevant experience to the role
- Highlight 2-3 specific achievements with measurable impact from the candidate's background
- Show genuine interest in the company and role
- Close with a clear call to action
- Tone: confident but not arrogant, professional, data-driven
- Do NOT use generic phrases like "I am writing to express my interest"
- Address it to "Hiring Team" since we don't know the hiring manager's name
- Keep it under 350 words

Return only the cover letter text, no subject line or meta-commentary."""

    return (await chat(prompt, json_mode=False, override=override)).strip()
```

- [ ] **Step 3: Verify `score_job` forwards the override (falls back to its except-branch default without a live provider)**

```powershell
python -c "
import asyncio
from backend.models import Job
from backend.services.matcher import score_job
job = Job(id='1', title='Data Engineer', company='X', location='Remote', description='some job description', url='http://x', source='test')
async def main():
    result = await score_job(job, 'profile text', override={'provider': 'bogus'})
    print(result)
asyncio.run(main())
"
```

Expected output: `{'score': 50, 'summary': 'Could not score this job.', 'matched_skills': [], 'missing_skills': []}` (proves the bogus override reached `chat()` inside `score_job` and was caught by its existing except-branch)

- [ ] **Step 4: Verify `suggest_queries` and `generate` forward the override**

```powershell
python -c "
import asyncio
from backend.services.matcher import suggest_queries
async def main():
    print(await suggest_queries('profile text', override={'provider': 'bogus'}))
asyncio.run(main())
"
```

Expected output: `[]`

```powershell
python -c "
import asyncio
from backend.models import CoverLetterRequest
from backend.services.cover_letter import generate
req = CoverLetterRequest(job_id='1', job_title='DE', company='X', description='desc')
async def main():
    try:
        await generate(req, 'profile', override={'provider': 'bogus'})
    except ValueError as e:
        print('GOOD:', e)
asyncio.run(main())
"
```

Expected output: `GOOD: Unknown LLM_PROVIDER: 'bogus'. Use ollama, openrouter, or anthropic.`

- [ ] **Step 5: Commit**

```powershell
git add backend/services/matcher.py backend/services/cover_letter.py
git commit -m "feat: thread LLM override through matcher and cover letter services"
```

---

### Task 3: Session storage + `/api/settings` endpoints in `main.py`

**Files:**
- Modify: `backend/main.py`

**Interfaces:**
- Consumes from Task 1: `LLMSettings` from `backend.models`; `chat(prompt, override=...)` from `backend.services.llm`
- Consumes from Task 2: `matcher.score_job(job, profile, override=...)`, `matcher.suggest_queries(text, override=...)`, `cover_letter.generate(req, profile, override=...)`
- Produces: `GET /api/settings` → `{"provider": str, "model": str | None, "base_url": str | None, "has_api_key": bool}`; `POST /api/settings` (body: `LLMSettings`) → `200 {"status": "ok", "provider": str}` or `400 {"detail": str}` — consumed by Task 5 (frontend)

- [ ] **Step 1: Add imports**

At the top of `backend/main.py`, change:

```python
from backend.models import Job, SearchRequest, CoverLetterRequest
```

to:

```python
import httpx
from backend.models import Job, SearchRequest, CoverLetterRequest, LLMSettings
from backend.services.llm import chat as llm_chat
```

- [ ] **Step 2: Initialize `llm_override` in session state**

Find:

```python
def _get_session(request: Request, response: Response) -> dict:
    session_id = request.cookies.get(SESSION_COOKIE)
    if not session_id or session_id not in _sessions:
        session_id = uuid.uuid4().hex
        response.set_cookie(SESSION_COOKIE, session_id, httponly=True, samesite="lax")
        _sessions[session_id] = {"profile": "", "scores": {}, "suggestions": []}
    return _sessions[session_id]
```

Replace with:

```python
def _get_session(request: Request, response: Response) -> dict:
    session_id = request.cookies.get(SESSION_COOKIE)
    if not session_id or session_id not in _sessions:
        session_id = uuid.uuid4().hex
        response.set_cookie(SESSION_COOKIE, session_id, httponly=True, samesite="lax")
        _sessions[session_id] = {"profile": "", "scores": {}, "suggestions": [], "llm_override": None}
    return _sessions[session_id]
```

- [ ] **Step 3: Add the `/api/settings` endpoints**

Add these two routes after `cv_status` and before `search_jobs`:

```python
@app.get("/api/settings")
async def get_settings(request: Request, response: Response):
    session = _get_session(request, response)
    override = session.get("llm_override")
    if not override:
        return {"provider": "default", "model": None, "base_url": None, "has_api_key": False}
    return {
        "provider": override.get("provider"),
        "model": override.get("model"),
        "base_url": override.get("base_url"),
        "has_api_key": bool(override.get("api_key")),
    }


@app.post("/api/settings")
async def save_settings(settings: LLMSettings, request: Request, response: Response):
    session = _get_session(request, response)

    if settings.provider == "default":
        session["llm_override"] = None
        return {"status": "ok", "provider": "default"}

    api_key = settings.api_key
    existing = session.get("llm_override")
    if not api_key and existing and existing.get("provider") == settings.provider:
        api_key = existing.get("api_key")
    if not api_key and settings.provider in ("openrouter", "anthropic"):
        raise HTTPException(status_code=400, detail="API key required")

    candidate = {
        "provider": settings.provider,
        "api_key": api_key,
        "base_url": settings.base_url,
        "model": settings.model,
    }

    try:
        await llm_chat("Reply with OK.", override=candidate)
    except httpx.HTTPStatusError as e:
        code = e.response.status_code
        if code in (401, 403):
            raise HTTPException(status_code=400, detail="Invalid API key")
        if code == 404:
            raise HTTPException(status_code=400, detail="Model not found")
        if code == 429:
            raise HTTPException(status_code=400, detail="Rate limited — try again shortly")
        raise HTTPException(status_code=400, detail="Connection test failed")
    except (httpx.ConnectError, httpx.TimeoutException):
        target = candidate["base_url"] or settings.provider
        raise HTTPException(status_code=400, detail=f"Could not reach {target}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"[Settings] unexpected error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=400, detail="Connection test failed")

    session["llm_override"] = candidate
    print(f"[Settings] session updated → provider={settings.provider}")
    return {"status": "ok", "provider": settings.provider}
```

> Note: `ValueError` is caught here too because an unresolvable provider string reaching `chat()` raises `ValueError` (see Task 1) — this turns it into a clean `400` instead of an unhandled `500`.

- [ ] **Step 4: Wire `override` into the three existing call sites**

In `get_job`, change:

```python
        score_data = await matcher.score_job(job, profile)
```

to:

```python
        score_data = await matcher.score_job(job, profile, override=session.get("llm_override"))
```

In `upload_cv`, change:

```python
    session["suggestions"] = await matcher.suggest_queries(text)
```

to:

```python
    session["suggestions"] = await matcher.suggest_queries(text, override=session.get("llm_override"))
```

In `gen_cover_letter`, change:

```python
    text = await cover_letter.generate(req, profile)
```

to:

```python
    text = await cover_letter.generate(req, profile, override=session.get("llm_override"))
```

- [ ] **Step 5: Verify the app still imports and the new routes are registered**

```powershell
python -c "from backend.main import app; print(sorted(r.path for r in app.routes if 'settings' in r.path))"
```

Expected output: `['/api/settings', '/api/settings']` (one `GET`, one `POST`, same path)

- [ ] **Step 6: Commit**

```powershell
git add backend/main.py
git commit -m "feat: add /api/settings endpoints and wire LLM override into session"
```

---

### Task 4: Settings modal markup + styling

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/static/style.css`

**Interfaces:**
- Produces DOM element IDs consumed by Task 5's JS: `settings-btn`, `settings-indicator`, `settings-modal-overlay`, `settings-modal-close`, `settings-provider`, `settings-fields-ollama`, `settings-fields-openrouter`, `settings-fields-anthropic`, `settings-ollama-url`, `settings-ollama-model`, `settings-openrouter-key`, `settings-openrouter-model`, `settings-anthropic-key`, `settings-anthropic-model`, `settings-status`, `settings-save-btn`, `settings-spinner`

- [ ] **Step 1: Add the gear icon to the header in `frontend/index.html`**

Find:

```html
  <header>
    <div class="header-inner">
      <div class="logo">Job Seeker</div>
    </div>
  </header>
```

Replace with:

```html
  <header>
    <div class="header-inner">
      <div class="logo">Job Seeker</div>
      <button id="settings-btn" class="settings-btn" title="LLM provider settings" aria-label="LLM provider settings">
        &#9881; <span id="settings-indicator" class="settings-indicator">Default</span>
      </button>
    </div>
  </header>
```

- [ ] **Step 2: Add the settings modal markup**

Find the closing `</div>` of the job detail modal (right before `<script src="/static/app.js"></script>`):

```html
  <script src="/static/app.js"></script>
```

Replace with (adding the new modal above the script tag):

```html
  <!-- Settings Modal -->
  <div id="settings-modal-overlay" class="modal-overlay hidden" role="dialog" aria-modal="true">
    <div class="modal settings-modal">
      <button class="modal-close" id="settings-modal-close" aria-label="Close">&times;</button>
      <h2>LLM Provider Settings</h2>
      <p class="settings-desc">Use your own AI provider instead of the app's default. Your key is stored only for this browser session and is sent only to the provider you choose.</p>

      <div class="settings-field">
        <label for="settings-provider">Provider</label>
        <select id="settings-provider">
          <option value="default">Default (app-provided)</option>
          <option value="ollama">Ollama (your own server)</option>
          <option value="openrouter">OpenRouter</option>
          <option value="anthropic">Anthropic</option>
        </select>
      </div>

      <div id="settings-fields-ollama" class="settings-provider-fields hidden">
        <div class="settings-field">
          <label for="settings-ollama-url">Base URL</label>
          <input type="text" id="settings-ollama-url" placeholder="http://localhost:11434" />
        </div>
        <div class="settings-field">
          <label for="settings-ollama-model">Model</label>
          <input type="text" id="settings-ollama-model" placeholder="gemma4:e4b" />
        </div>
      </div>

      <div id="settings-fields-openrouter" class="settings-provider-fields hidden">
        <div class="settings-field">
          <label for="settings-openrouter-key">API Key</label>
          <input type="password" id="settings-openrouter-key" placeholder="sk-or-..." />
        </div>
        <div class="settings-field">
          <label for="settings-openrouter-model">Model</label>
          <input type="text" id="settings-openrouter-model" placeholder="google/gemma-3-4b-it:free" />
        </div>
      </div>

      <div id="settings-fields-anthropic" class="settings-provider-fields hidden">
        <div class="settings-field">
          <label for="settings-anthropic-key">API Key</label>
          <input type="password" id="settings-anthropic-key" placeholder="sk-ant-..." />
        </div>
        <div class="settings-field">
          <label for="settings-anthropic-model">Model (optional)</label>
          <input type="text" id="settings-anthropic-model" placeholder="claude-sonnet-4-6" />
        </div>
      </div>

      <div id="settings-status" class="settings-status hidden"></div>

      <div class="settings-actions">
        <button id="settings-save-btn" class="cv-upload-btn">Save</button>
        <span id="settings-spinner" class="spinner hidden"></span>
      </div>
    </div>
  </div>

  <script src="/static/app.js"></script>
```

- [ ] **Step 3: Add styling to `frontend/static/style.css`**

Find the existing `.header-inner` rule:

```css
.header-inner {
  max-width: 1100px;
  margin: 0 auto;
  width: 100%;
  display: flex;
  align-items: center;
}
```

Replace with:

```css
.header-inner {
  max-width: 1100px;
  margin: 0 auto;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
```

Then append this new section right after the `/* ===== CV Upload Bar ===== */` block (after the `.cv-remove-btn:hover` rule, before `/* ===== Scrollbar ===== */`):

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

.settings-modal { max-width: 460px; }
.settings-desc { color: var(--text-muted); font-size: 0.82rem; margin-bottom: 18px; padding-right: 20px; }
.settings-field { margin-bottom: 14px; }
.settings-field label {
  display: block;
  font-size: 0.78rem;
  color: var(--text-muted);
  margin-bottom: 5px;
}
.settings-field select,
.settings-field input {
  width: 100%;
  background: var(--bg);
  border: 1px solid var(--border);
  color: var(--text);
  border-radius: var(--radius-sm);
  padding: 7px 10px;
  font-size: 0.88rem;
  font-family: inherit;
}
.settings-field select:focus,
.settings-field input:focus { outline: none; border-color: var(--accent); }
.settings-status {
  font-size: 0.82rem;
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  margin-bottom: 14px;
}
.settings-status.error { background: rgba(239,68,68,0.1); color: var(--red); }
.settings-status.success { background: rgba(34,197,94,0.1); color: var(--green); }
.settings-actions { display: flex; align-items: center; gap: 10px; }
```

- [ ] **Step 4: Verify the markup and styles are present**

```powershell
Select-String -Path frontend/index.html -Pattern "settings-modal-overlay","settings-btn" | Measure-Object | Select-Object -ExpandProperty Count
Select-String -Path frontend/static/style.css -Pattern "\.settings-btn" | Measure-Object | Select-Object -ExpandProperty Count
```

Expected: both counts are `1` or greater (non-zero — confirms the markup and CSS block were actually inserted).

- [ ] **Step 5: Commit**

```powershell
git add frontend/index.html frontend/static/style.css
git commit -m "feat: add LLM settings modal markup and styling"
```

---

### Task 5: Settings modal JS logic

**Files:**
- Modify: `frontend/static/app.js`

**Interfaces:**
- Consumes from Task 3: `GET /api/settings` → `{provider, model, base_url, has_api_key}`; `POST /api/settings` (JSON body matching `LLMSettings`) → `200 {status, provider}` or non-2xx with `{detail}`
- Consumes from Task 4: all `settings-*` element IDs listed in Task 4's Interfaces

- [ ] **Step 1: Append settings logic to `frontend/static/app.js`**

Add this block at the end of the file:

```javascript
/* ===== LLM Settings ===== */
const settingsBtn          = document.getElementById('settings-btn');
const settingsIndicator    = document.getElementById('settings-indicator');
const settingsModalOverlay = document.getElementById('settings-modal-overlay');
const settingsModalClose   = document.getElementById('settings-modal-close');
const settingsProvider     = document.getElementById('settings-provider');
const settingsSaveBtn      = document.getElementById('settings-save-btn');
const settingsSpinner      = document.getElementById('settings-spinner');
const settingsStatus       = document.getElementById('settings-status');

const settingsProviderFields = {
  ollama: document.getElementById('settings-fields-ollama'),
  openrouter: document.getElementById('settings-fields-openrouter'),
  anthropic: document.getElementById('settings-fields-anthropic'),
};

const settingsInputs = {
  ollama: {
    url: document.getElementById('settings-ollama-url'),
    model: document.getElementById('settings-ollama-model'),
  },
  openrouter: {
    key: document.getElementById('settings-openrouter-key'),
    model: document.getElementById('settings-openrouter-model'),
  },
  anthropic: {
    key: document.getElementById('settings-anthropic-key'),
    model: document.getElementById('settings-anthropic-model'),
  },
};

function updateProviderFieldsVisibility() {
  const provider = settingsProvider.value;
  Object.entries(settingsProviderFields).forEach(([name, el]) => {
    el.classList.toggle('hidden', name !== provider);
  });
}
settingsProvider.addEventListener('change', updateProviderFieldsVisibility);

function updateSettingsIndicator(provider) {
  settingsIndicator.textContent = provider === 'default'
    ? 'Default'
    : provider.charAt(0).toUpperCase() + provider.slice(1);
}

async function loadSettings() {
  try {
    const resp = await fetch('/api/settings');
    const data = await resp.json();
    updateSettingsIndicator(data.provider);
    settingsProvider.value = data.provider;

    if (data.provider === 'ollama') {
      settingsInputs.ollama.url.value = data.base_url || '';
      settingsInputs.ollama.model.value = data.model || '';
    } else if (data.provider === 'openrouter') {
      settingsInputs.openrouter.model.value = data.model || '';
      settingsInputs.openrouter.key.placeholder = data.has_api_key ? '•••• saved' : 'sk-or-...';
    } else if (data.provider === 'anthropic') {
      settingsInputs.anthropic.model.value = data.model || '';
      settingsInputs.anthropic.key.placeholder = data.has_api_key ? '•••• saved' : 'sk-ant-...';
    }
    updateProviderFieldsVisibility();
  } catch {}
}

settingsBtn.addEventListener('click', () => {
  settingsStatus.classList.add('hidden');
  settingsModalOverlay.classList.remove('hidden');
  document.body.style.overflow = 'hidden';
});
settingsModalClose.addEventListener('click', closeSettingsModal);
settingsModalOverlay.addEventListener('click', e => { if (e.target === settingsModalOverlay) closeSettingsModal(); });

function closeSettingsModal() {
  settingsModalOverlay.classList.add('hidden');
  document.body.style.overflow = '';
}

settingsSaveBtn.addEventListener('click', async () => {
  const provider = settingsProvider.value;
  const body = { provider };

  if (provider === 'ollama') {
    body.base_url = settingsInputs.ollama.url.value.trim() || null;
    body.model = settingsInputs.ollama.model.value.trim() || null;
  } else if (provider === 'openrouter') {
    body.api_key = settingsInputs.openrouter.key.value.trim() || null;
    body.model = settingsInputs.openrouter.model.value.trim() || null;
  } else if (provider === 'anthropic') {
    body.api_key = settingsInputs.anthropic.key.value.trim() || null;
    body.model = settingsInputs.anthropic.model.value.trim() || null;
  }

  settingsSaveBtn.disabled = true;
  settingsSpinner.classList.remove('hidden');
  settingsStatus.classList.add('hidden');

  try {
    const resp = await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || 'Save failed');

    updateSettingsIndicator(data.provider);
    settingsStatus.textContent = 'Saved.';
    settingsStatus.className = 'settings-status success';
    settingsStatus.classList.remove('hidden');
    setTimeout(closeSettingsModal, 900);
  } catch (e) {
    settingsStatus.textContent = e.message;
    settingsStatus.className = 'settings-status error';
    settingsStatus.classList.remove('hidden');
  } finally {
    settingsSaveBtn.disabled = false;
    settingsSpinner.classList.add('hidden');
  }
});

loadSettings();
```

- [ ] **Step 2: Verify with the dev server running**

Start the server:

```powershell
.\run.ps1
```

In a second terminal, exercise the new endpoints directly:

```powershell
# Should return the default state (no cookie yet, but FastAPI still creates a session)
Invoke-RestMethod -Uri http://localhost:8000/api/settings -Method Get

# Should fail cleanly (no api_key) rather than crash
Invoke-RestMethod -Uri http://localhost:8000/api/settings -Method Post -ContentType "application/json" -Body '{"provider":"openrouter"}' -SkipHttpErrorCheck
```

Expected: the `GET` returns `{"provider":"default","model":null,"base_url":null,"has_api_key":false}`. The `POST` returns HTTP 400 with `{"detail":"API key required"}`.

- [ ] **Step 3: Verify in the browser**

With the server still running, open `http://localhost:8000`, hard refresh (`Ctrl+Shift+R`), then:

1. Confirm a gear icon with "Default" next to it appears top-right of the header.
2. Click it — modal opens, provider dropdown shows "Default (app-provided)" selected.
3. Switch the dropdown to "Ollama (your own server)" — the Base URL / Model fields appear.
4. Leave both blank (falls back to `.env` defaults) and click Save. If Ollama is running locally, this should succeed, show "Saved.", close the modal, and update the indicator to "Ollama". If Ollama is not running, it should show a red inline error instead of crashing the page.
5. Reopen the modal, switch to "OpenRouter", leave the API key blank, click Save — should show the inline error "API key required" without closing the modal.
6. Search for a job and open its detail modal — scoring should still work end-to-end using whichever provider is currently saved (or the default, if you reverted).

Stop the server (`Ctrl+C`) once verified.

- [ ] **Step 4: Commit**

```powershell
git add frontend/static/app.js
git commit -m "feat: wire LLM settings modal to /api/settings"
```

---

## Post-Implementation Smoke Test

After all five tasks are committed:

1. Run `.\run.ps1`, open `http://localhost:8000`, hard refresh.
2. Upload a CV, confirm suggestions still populate (uses default provider since no override saved yet).
3. Open Settings, configure OpenRouter with a real API key and model (e.g. `google/gemma-3-4b-it:free`), Save — should succeed and close the modal.
4. Search for a job, click a card — the score should come back scored via OpenRouter (check the server console; no `[LLM]` errors).
5. Generate a cover letter on that job — should succeed.
6. Reopen Settings, switch back to "Default", Save — subsequent scoring should go back to using the server's configured default provider.
7. Restart the server (`Ctrl+C` then `.\run.ps1` again) and confirm the settings indicator resets to "Default" (session cleared, matching CV-upload behavior).

If any step hangs or 500s, check the server console for `[Settings]` or `[Matcher]` error lines.
