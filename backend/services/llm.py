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
