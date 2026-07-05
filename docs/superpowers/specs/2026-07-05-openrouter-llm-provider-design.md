# Design: OpenRouter LLM Provider Support

**Date:** 2026-07-05  
**Status:** Approved

---

## Summary

Add OpenRouter as a third LLM provider alongside the existing Ollama and Anthropic options. Replace the `USE_OLLAMA` boolean toggle with a `LLM_PROVIDER` string env var that accepts `ollama`, `openrouter`, or `anthropic`.

---

## Motivation

- OpenRouter aggregates hundreds of models under a single OpenAI-compatible API, making it the preferred production path.
- Ollama remains available for fully local/offline use.
- Anthropic is retained for direct SDK access (direct billing, no routing overhead).

---

## Scope

Files changed:
- `backend/config.py` — replace `USE_OLLAMA` with `LLM_PROVIDER`; add `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`
- `backend/services/llm.py` — add `_openrouter_chat()`; update `chat()` dispatcher; update imports
- `.env.example` — replace `USE_OLLAMA` with `LLM_PROVIDER`; add OpenRouter vars
- `CLAUDE.md` — update env vars table and common issues table

Files unchanged: `main.py`, `matcher.py`, `cover_letter.py`, all sources — they call `llm.chat()` with no provider knowledge.

---

## Configuration

### `.env.example` (new shape)

```
# Provider: ollama | openrouter | anthropic
LLM_PROVIDER=ollama

# Ollama (local, free)
OLLAMA_MODEL=gemma4:e4b
OLLAMA_BASE_URL=http://localhost:11434

# OpenRouter (production)
OPENROUTER_API_KEY=
OPENROUTER_MODEL=              # e.g. google/gemma-3-4b-it:free, anthropic/claude-sonnet-4-5

# Anthropic (direct cloud)
ANTHROPIC_API_KEY=

# RapidAPI for JSearch (unchanged)
RAPIDAPI_KEY=
```

### `config.py` changes

- Remove: `USE_OLLAMA`
- Add: `LLM_PROVIDER` (str, default `"ollama"`)
- Add: `OPENROUTER_API_KEY` (str, default `""`)
- Add: `OPENROUTER_MODEL` (str, default `""`)

### Breaking change

Any existing `.env` using `USE_OLLAMA=true` must be updated to `LLM_PROVIDER=ollama`. `USE_OLLAMA=false` becomes `LLM_PROVIDER=anthropic` or `LLM_PROVIDER=openrouter` depending on intent.

---

## LLM Service (`llm.py`)

### `chat()` dispatcher

```python
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
```

### New `_openrouter_chat()`

- Endpoint: `https://openrouter.ai/api/v1/chat/completions`
- Auth: `Authorization: Bearer {OPENROUTER_API_KEY}`
- No new dependencies — uses existing `httpx`
- Temperature: `0.1` (consistent with Ollama)
- Timeout: `120s` (consistent with Ollama)
- Response path: `choices[0].message.content`

### `_ollama_chat()` and `_anthropic_chat()`

Unchanged.

---

## Startup Validation

On import of `llm.py`, validate required keys for the configured provider:

- `LLM_PROVIDER=openrouter` → `OPENROUTER_API_KEY` must be non-empty; `OPENROUTER_MODEL` must be non-empty
- `LLM_PROVIDER=anthropic` → `ANTHROPIC_API_KEY` must be non-empty
- `LLM_PROVIDER=ollama` → no key required

Raise `ValueError` with a clear message if validation fails. This surfaces misconfiguration at startup rather than on the first user request.

---

## CLAUDE.md Updates

### Env vars table (replace `USE_OLLAMA` row)

| Variable | Purpose |
|---|---|
| `LLM_PROVIDER` | `ollama` / `openrouter` / `anthropic` |
| `OLLAMA_MODEL` | Ollama model name |
| `OLLAMA_BASE_URL` | Ollama server URL |
| `OPENROUTER_API_KEY` | Required when `LLM_PROVIDER=openrouter` |
| `OPENROUTER_MODEL` | OpenRouter model string (e.g. `google/gemma-3-4b-it:free`) |
| `ANTHROPIC_API_KEY` | Required when `LLM_PROVIDER=anthropic` |
| `RAPIDAPI_KEY` | Enables JSearch |

### Common issues table (add row)

| Symptom | Cause | Fix |
|---|---|---|
| `ValueError: Unknown LLM_PROVIDER` | Typo or old `USE_OLLAMA` in `.env` | Set `LLM_PROVIDER=ollama`, `openrouter`, or `anthropic` |
| OpenRouter returns 401 | Missing/invalid `OPENROUTER_API_KEY` | Check `.env` and openrouter.ai dashboard |
| OpenRouter returns 404 on model | Invalid `OPENROUTER_MODEL` string | Check model ID at openrouter.ai/models |

---

## Out of Scope

- No streaming support (not used today)
- No per-request model override
- No fallback chaining between providers
- No `json_mode` for OpenRouter or Anthropic (only Ollama supports it natively; callers already handle parsing)
