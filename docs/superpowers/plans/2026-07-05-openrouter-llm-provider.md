# OpenRouter LLM Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add OpenRouter as a third LLM provider and replace the `USE_OLLAMA` boolean with a `LLM_PROVIDER` string env var (`ollama` | `openrouter` | `anthropic`).

**Architecture:** Single dispatcher function `chat()` in `llm.py` routes to one of three private functions based on `LLM_PROVIDER`. All config vars are read from `.env` via `config.py`. No new dependencies — OpenRouter uses the already-imported `httpx`.

**Tech Stack:** Python 3.12, FastAPI, httpx, python-dotenv, anthropic SDK (existing)

## Global Constraints

- No new pip dependencies — use `httpx` for OpenRouter (already in requirements)
- `LLM_PROVIDER` accepts exactly three values: `ollama`, `openrouter`, `anthropic` — anything else raises `ValueError` at startup
- OpenRouter endpoint: `https://openrouter.ai/api/v1/chat/completions`
- Temperature `0.1` and timeout `120s` for OpenRouter (consistent with Ollama)
- `_ollama_chat()` and `_anthropic_chat()` must not be modified

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `backend/config.py` | Modify | Remove `USE_OLLAMA`; add `LLM_PROVIDER`, `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` |
| `backend/services/llm.py` | Modify | Add `_openrouter_chat()`; update `chat()` dispatcher; add startup validation; update imports |
| `.env.example` | Modify | Replace `USE_OLLAMA` with `LLM_PROVIDER`; add OpenRouter section |
| `CLAUDE.md` | Modify | Update env vars table; add OpenRouter rows to common issues table |

---

### Task 1: Update config and env template

**Files:**
- Modify: `backend/config.py`
- Modify: `.env.example`

**Interfaces:**
- Produces: `LLM_PROVIDER: str`, `OPENROUTER_API_KEY: str`, `OPENROUTER_MODEL: str` — imported by `llm.py` in Task 2
- Removes: `USE_OLLAMA: bool` — Task 2 must not import this

- [ ] **Step 1: Update `backend/config.py`**

Replace the file content (keep `ANTHROPIC_API_KEY`, `RAPIDAPI_KEY`, Ollama vars; remove `USE_OLLAMA`; add three new vars):

```python
import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")

# Ollama settings
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:e4b")

# Provider selection: ollama | openrouter | anthropic
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()

# OpenRouter settings
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "")

USER_PROFILE = """
Name: Md. Minhajul Islam
...
"""  # Leave USER_PROFILE block completely unchanged — only touch the vars above it
```

> **Important:** `USER_PROFILE` is a large multiline string below these vars. Do not touch it — only edit the variable declarations above it.

- [ ] **Step 2: Update `.env.example`**

Replace the file with:

```
# ── LLM Provider ──────────────────────────────────────────────────
# ollama | openrouter | anthropic
LLM_PROVIDER=ollama

# ── Ollama (local, free) ──────────────────────────────────────────
OLLAMA_MODEL=gemma4:e4b          # run: ollama list  to see your models
OLLAMA_BASE_URL=http://localhost:11434

# ── OpenRouter (production) ───────────────────────────────────────
OPENROUTER_API_KEY=
OPENROUTER_MODEL=                # e.g. google/gemma-3-4b-it:free

# ── Anthropic API (direct cloud) ─────────────────────────────────
ANTHROPIC_API_KEY=

# ── Optional: RapidAPI for JSearch (LinkedIn, Indeed, Glassdoor) ──
RAPIDAPI_KEY=
```

- [ ] **Step 3: Verify config imports cleanly**

Run in PowerShell from the project root:

```powershell
python -c "from backend.config import LLM_PROVIDER, OPENROUTER_API_KEY, OPENROUTER_MODEL; print(LLM_PROVIDER, repr(OPENROUTER_API_KEY), repr(OPENROUTER_MODEL))"
```

Expected output (with default `.env` or no `.env`):
```
ollama '' ''
```

If you see `ImportError: cannot import name 'USE_OLLAMA'`, check that you removed it from `config.py`.

- [ ] **Step 4: Commit**

```powershell
git add backend/config.py .env.example
git commit -m "config: replace USE_OLLAMA with LLM_PROVIDER; add OpenRouter vars"
```

---

### Task 2: Update LLM service

**Files:**
- Modify: `backend/services/llm.py`

**Interfaces:**
- Consumes from Task 1: `LLM_PROVIDER: str`, `OPENROUTER_API_KEY: str`, `OPENROUTER_MODEL: str` from `backend.config`
- Produces: `chat(prompt: str, json_mode: bool = False) -> str` — unchanged signature, unchanged callers

- [ ] **Step 1: Rewrite `backend/services/llm.py`**

Replace the entire file with:

```python
"""
Unified LLM client.
Controlled via .env:
  LLM_PROVIDER=ollama       + OLLAMA_MODEL=...          → local Ollama
  LLM_PROVIDER=openrouter   + OPENROUTER_API_KEY=...    → OpenRouter cloud
  LLM_PROVIDER=anthropic    + ANTHROPIC_API_KEY=...     → Anthropic direct
"""

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

# Fail fast at startup if required keys are missing
if LLM_PROVIDER == "openrouter":
    if not OPENROUTER_API_KEY:
        raise ValueError("LLM_PROVIDER=openrouter requires OPENROUTER_API_KEY in .env")
    if not OPENROUTER_MODEL:
        raise ValueError("LLM_PROVIDER=openrouter requires OPENROUTER_MODEL in .env")
elif LLM_PROVIDER == "anthropic":
    if not ANTHROPIC_API_KEY:
        raise ValueError("LLM_PROVIDER=anthropic requires ANTHROPIC_API_KEY in .env")


async def chat(prompt: str, json_mode: bool = False) -> str:
    if LLM_PROVIDER == "ollama":
        return await _ollama_chat(prompt, json_mode)
    elif LLM_PROVIDER == "openrouter":
        return await _openrouter_chat(prompt)
    elif LLM_PROVIDER == "anthropic":
        return await _anthropic_chat(prompt)
    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER: {LLM_PROVIDER!r}. Use ollama, openrouter, or anthropic."
        )


async def _ollama_chat(prompt: str, json_mode: bool) -> str:
    payload: dict = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.1},
    }
    if json_mode:
        payload["format"] = "json"

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["message"]["content"]


async def _openrouter_chat(prompt: str) -> str:
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
            json={
                "model": OPENROUTER_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


async def _anthropic_chat(prompt: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-sonnet-4-6",
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

- [ ] **Step 2: Verify Ollama path imports cleanly (default config)**

With `.env` having `LLM_PROVIDER=ollama` (or no `.env`):

```powershell
python -c "from backend.services.llm import chat; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Verify startup validation fires for bad config**

```powershell
python -c "
import os; os.environ['LLM_PROVIDER'] = 'openrouter'; os.environ['OPENROUTER_API_KEY'] = ''; os.environ['OPENROUTER_MODEL'] = ''
from importlib import import_module, invalidate_caches
invalidate_caches()
try:
    import backend.services.llm as m
    import importlib; importlib.reload(m)
except ValueError as e:
    print('GOOD:', e)
"
```

Expected output contains: `GOOD: LLM_PROVIDER=openrouter requires OPENROUTER_API_KEY`

> Note: Module-level validation fires on import, so the easiest manual check is to temporarily set `LLM_PROVIDER=openrouter` with empty keys in your `.env`, restart the server with `.\run.ps1`, and confirm you see the `ValueError` in the console immediately on startup (before any request is made).

- [ ] **Step 4: Commit**

```powershell
git add backend/services/llm.py
git commit -m "feat: add OpenRouter provider; three-way LLM_PROVIDER dispatcher"
```

---

### Task 3: Update docs

**Files:**
- Modify: `CLAUDE.md`

**Interfaces:**
- No code interfaces — documentation only

- [ ] **Step 1: Update the env vars table in `CLAUDE.md`**

Find the `## Environment variables` section. Replace the entire table with:

```markdown
| Variable | Purpose |
|---|---|
| `LLM_PROVIDER` | `ollama` / `openrouter` / `anthropic` (default: `ollama`) |
| `OLLAMA_MODEL` | Ollama model name (e.g. `gemma4:e4b`) |
| `OLLAMA_BASE_URL` | Ollama server (default `http://localhost:11434`) |
| `OPENROUTER_API_KEY` | Required when `LLM_PROVIDER=openrouter` |
| `OPENROUTER_MODEL` | OpenRouter model string (e.g. `google/gemma-3-4b-it:free`) |
| `ANTHROPIC_API_KEY` | Required when `LLM_PROVIDER=anthropic` |
| `RAPIDAPI_KEY` | Enables JSearch — LinkedIn/Indeed/Glassdoor results |
```

- [ ] **Step 2: Add OpenRouter rows to the common issues table in `CLAUDE.md`**

Find the `## Common issues` section. Add these three rows to the existing table:

```markdown
| `ValueError: Unknown LLM_PROVIDER` | Typo or old `USE_OLLAMA` in `.env` | Set `LLM_PROVIDER=ollama`, `openrouter`, or `anthropic` |
| OpenRouter 401 on scoring/cover letter | Missing/invalid `OPENROUTER_API_KEY` | Check `.env` and openrouter.ai dashboard |
| OpenRouter 404 on model | Invalid `OPENROUTER_MODEL` string | Check model ID at openrouter.ai/models |
```

- [ ] **Step 3: Update the "Running the app" section note about AI providers**

Find this line in `CLAUDE.md`:

```
| USE_OLLAMA | `true` = local Ollama, `false` = Anthropic cloud |
```

If it still exists anywhere in the document (e.g. in architecture notes), replace every occurrence of `USE_OLLAMA` with `LLM_PROVIDER`.

- [ ] **Step 4: Commit**

```powershell
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md for LLM_PROVIDER and OpenRouter"
```

---

## Post-Implementation Smoke Test

After all three tasks are committed, do a full end-to-end smoke test:

1. Set `LLM_PROVIDER=openrouter`, `OPENROUTER_API_KEY=<your key>`, `OPENROUTER_MODEL=google/gemma-3-4b-it:free` in `.env`
2. Run `.\run.ps1`
3. Open `http://localhost:8000`, search for "data engineer"
4. Click a job card — the score should populate via OpenRouter
5. Click "Generate Cover Letter" on a scored job — should return a letter

If step 4 or 5 hangs or errors, check the server console for the provider name in error output.
