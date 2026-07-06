"""
Unified LLM client.
Controlled via .env:
  LLM_PROVIDER=ollama       + OLLAMA_MODEL=...          → local Ollama
  LLM_PROVIDER=openrouter   + OPENROUTER_API_KEY=...    → OpenRouter cloud
  LLM_PROVIDER=anthropic    + ANTHROPIC_API_KEY=...     → Anthropic direct
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


async def _openrouter_chat(prompt: str, max_retries: int = 3) -> str:
    backoff = 1.0
    async with httpx.AsyncClient(timeout=120) as client:
        for attempt in range(max_retries + 1):
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
                json={
                    "model": OPENROUTER_MODEL,
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
