# Design: Bring-Your-Own LLM Key

**Date:** 2026-07-07
**Status:** Approved

---

## Summary

Let each browser session configure its own LLM provider (Ollama server, OpenRouter, or Anthropic) with its own key/URL/model, overriding the server's `.env` defaults for that session only. Users who don't configure anything keep using the app's default provider exactly as today. Settings are entered via a modal, validated with a live test call before being saved, and held only in the existing in-memory, cookie-keyed session store (same place the uploaded CV and match scores already live) — no accounts, no database, no localStorage.

---

## Scope

**Files changed:**
- `backend/models.py` — add `LLMSettings` model
- `backend/services/llm.py` — `chat()` accepts an optional `override` dict; provider dispatch resolves each field (`provider`, `api_key`, `base_url`, `model`) from the override first, falling back to `.env` config
- `backend/services/matcher.py` — `score_job` and `suggest_queries` accept and pass through `override`
- `backend/services/cover_letter.py` — `generate` accepts and passes through `override`
- `backend/main.py` — add `llm_override: dict | None` to session state; add `GET /api/settings` and `POST /api/settings`; pass `session["llm_override"]` into the three call sites above
- `frontend/index.html` — add gear icon + settings modal markup
- `frontend/static/app.js` — modal open/close, form logic, save/validate call, status indicator
- `frontend/static/style.css` — modal field styling (reuses existing `.modal-overlay`/`.modal` classes)

**Files unchanged:** `backend/config.py`, `backend/sources/*` (job search keys stay server-only), `backend/services/llm.py`'s startup fail-fast checks (still validate the server's own `.env` default provider config, unrelated to per-session overrides)

---

## Backend

### `LLMSettings` model (`models.py`)

```python
class LLMSettings(BaseModel):
    provider: str            # "default" | "ollama" | "openrouter" | "anthropic"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
```

### Session state (`main.py`)

`_get_session()` initializes new sessions with `"llm_override": None` alongside the existing `profile`/`scores`/`suggestions` keys. `None` means "use `.env` defaults" (today's behavior).

### `llm.py`: `chat(prompt, json_mode=False, override: dict | None = None)`

Resolution per field, override wins if non-empty, else fall back to the matching `.env` constant:

| Field | Override key | Fallback |
|---|---|---|
| provider | `override["provider"]` (skip resolution entirely if `None`/`"default"`) | `LLM_PROVIDER` |
| Ollama base URL | `override["base_url"]` | `OLLAMA_BASE_URL` |
| Ollama model | `override["model"]` | `OLLAMA_MODEL` |
| OpenRouter key | `override["api_key"]` | `OPENROUTER_API_KEY` |
| OpenRouter model | `override["model"]` | `OPENROUTER_MODEL` |
| Anthropic key | `override["api_key"]` | `ANTHROPIC_API_KEY` |
| Anthropic model | `override["model"]` | `"claude-sonnet-4-6"` (currently hardcoded in `_anthropic_chat`) |

`_ollama_chat`, `_openrouter_chat`, `_anthropic_chat` gain explicit params for these resolved values instead of reading module-level constants directly, so `chat()` does the resolution once and passes plain values down.

### `matcher.score_job(job, profile, override=None)`, `matcher.suggest_queries(profile, ..., override=None)`, `cover_letter.generate(req, profile, override=None)`

Each just threads `override` through to its `chat(...)` call. No other logic changes.

### `GET /api/settings`

Reads `session["llm_override"]`. Returns:
```json
{"provider": "openrouter", "model": "google/gemma-3-4b-it:free", "base_url": null, "has_api_key": true}
```
or, with no override set:
```json
{"provider": "default", "model": null, "base_url": null, "has_api_key": false}
```
Never returns the raw `api_key` — used by the frontend to redraw the modal with current state without echoing secrets back.

### `POST /api/settings`

Body: `LLMSettings`. Flow:

1. If `provider == "default"`: clear `session["llm_override"] = None`, return `{"status": "ok", "provider": "default"}`.
2. Otherwise, build a candidate override dict. If `api_key` is blank/omitted and a key is already saved in the session for this exact provider, reuse the saved key (so editing just the model doesn't force re-entering the key). If the provider differs from what's currently saved, a blank `api_key` is an error (`400 "API key required"`).
3. Run one minimal validation call: `await chat("Reply with OK.", override=candidate)`.
4. On success: save `candidate` to `session["llm_override"]`, return `{"status": "ok", "provider": ...}`.
5. On failure: return `400` with a message mapped from the failure, not the raw exception (avoids ever surfacing header/key content):
   - `httpx.HTTPStatusError` with 401/403 → `"Invalid API key"`
   - `httpx.HTTPStatusError` with 404 → `"Model not found"`
   - `httpx.HTTPStatusError` with 429 → `"Rate limited — try again shortly"`
   - `httpx.ConnectError` / timeout → `"Could not reach <base_url or provider>"`
   - anything else → `"Connection test failed"`

### Call sites

```python
# GET /api/job/{job_id}
score_data = await matcher.score_job(job, profile, override=session["llm_override"])

# POST /api/cv (suggestions after upload)
session["suggestions"] = await matcher.suggest_queries(text, override=session["llm_override"])

# POST /api/cover-letter
text = await cover_letter.generate(req, profile, override=session["llm_override"])
```

---

## Frontend

### Gear icon + modal (`index.html`)

A gear icon sits near the CV upload area. Clicking it opens a new modal (reusing `.modal-overlay`/`.modal`), with:

- Provider `<select>`: Default / Ollama / OpenRouter / Anthropic
- Conditional fields based on selection:
  - **Default**: just explanatory text ("Uses the app's built-in provider.")
  - **Ollama**: Base URL (text, placeholder `http://localhost:11434`), Model (text, placeholder `gemma4:e4b`)
  - **OpenRouter**: API Key (password input), Model (text, placeholder `google/gemma-3-4b-it:free`)
  - **Anthropic**: API Key (password input), Model (text, placeholder `claude-sonnet-4-6`, optional)
- Single **Save** button
- Inline status area for spinner / success / error message

### JS logic (`app.js`)

- On page load: `GET /api/settings` → populate a small status indicator near the gear icon (e.g. "Using: Default" / "Using: OpenRouter") and pre-fill the modal's non-secret fields (`provider`, `model`, `base_url`) when it's opened; API key field stays blank with placeholder `"•••• saved"` if `has_api_key` is true
- Save click: `POST /api/settings` with form values (omit `api_key` if the field was left blank) → show spinner while pending
  - Success: close modal, update status indicator
  - Failure: show the returned error message inline, keep modal open, keep entered values
- "Use default" is just selecting "Default" from the dropdown and clicking Save (clears the override)

---

## Security

- The key is sent from the browser to this app's own backend (not directly to the provider), held only in the server-side in-memory session dict, and forwarded to the provider per LLM call
- Never logged, never written to disk, never echoed back in `GET /api/settings` responses
- Validation-failure messages are mapped from HTTP status codes rather than passing raw exception text to the client, so provider error bodies (which could theoretically echo request details) never reach the frontend

---

## Out of Scope

- `RAPIDAPI_KEY` (job search sources) — stays server-only, not user-configurable
- No localStorage caching — settings are session-only, cleared on server restart, same as CV upload today
- No accounts/auth — sessions remain anonymous cookie-based, same as today
- No model-list autocomplete/fetching from providers — model is a free-text field, matching the existing `.env` pattern
- No per-request override (e.g. "use OpenRouter just for this one cover letter") — one override applies to the whole session
