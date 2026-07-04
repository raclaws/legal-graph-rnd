"""LLM service — Anthropic client wrapper."""

from __future__ import annotations

import json
import os
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent.parent
SETTINGS_PATH = _PROJECT_ROOT / "data" / ".settings.json"
# Fallback: legacy location at project root
_LEGACY_SETTINGS_PATH = _PROJECT_ROOT / ".settings.json"


def _load_env():
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())


_load_env()


def _load_settings() -> dict:
    for path in (SETTINGS_PATH, _LEGACY_SETTINGS_PATH):
        if path.exists():
            try:
                return json.loads(path.read_text())
            except (json.JSONDecodeError, OSError):
                pass
    return {}


def _save_settings(data: dict):
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(data, indent=2))


def get_llm_config() -> tuple[str, str, str]:
    """Returns (api_key, base_url, model) from settings file, env fallback."""
    settings = _load_settings()
    api_key = settings.get("api_key") or os.environ.get("ANTHROPIC_API_KEY", "")
    base_url = settings.get("base_url") or os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
    model = settings.get("model") or os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
    return api_key, base_url, model


SYSTEM_PROMPT = """You are an Indonesian HR compliance assistant backed by a legal knowledge graph with 17 parsed regulations and 5,676 provisions.

RESPONSE FORMAT — return JSON:
{
  "hukum": [{"description": "fact + citation", "legal_basis": "PP/2021/35/Bab/II/Pasal/8", "severity": "high"}],
  "analisis": "interpretation text with inline citation markers like [1] [2] referencing hukum items by position (1-indexed)",
  "perlu_dikonfirmasi": [
    {"question": "...", "type": "select|number|text|file", "options": [...] or null, "key": "unique_key", "why": "reason this matters"}
  ] or null,
  "intent": "severance_calc|ump_check|bpjs_rates|pkwt|phi_dispute|general_hr",
  "params": {
    "years_of_service": null,
    "monthly_salary": null,
    "termination_reason": null,
    "province": null
  }
}

RULES:
- hukum: ONLY graph-backed facts. EVERY hukum item MUST have a non-empty legal_basis (node_id format like PP/2021/35/Bab/II/Pasal/8). If you cannot cite a specific Pasal, do NOT put it in hukum — put it in analisis instead.
- analisis: Your reasoning/advice. Use [1], [2], [3] etc to reference hukum items by position. Always labeled as interpretation.
- perlu_dikonfirmasi: ONLY when the answer would change the legal outcome. Rules:
  1. Maximum 2 questions per response. Never more.
  2. Never ask if you can give a useful answer without it — give the answer first, then ask to refine.
  3. Never ask what can be inferred from context (e.g., don't ask "apakah ini PKWT?" if the user already said "kontrak saya").
  4. Never ask generic fact-finding questions ("berapa lama masa kerja?") unless calculating severance or UMP comparison.
  5. If unsure whether to ask: give your best answer with assumptions stated, then offer "jika berbeda, beri tahu saya" at the end of analisis instead.
  6. Prefer type "select" with concrete options over open-ended "text".
- Return ONLY valid JSON, no markdown.

KNOWLEDGE (from graph — 17 regulations):
- PP 35/2021: PKWT (max 5 tahun, Pasal 8), Alih Daya (Bab III), Waktu Kerja (Bab IV), PHK/Severance (Bab V)
- PP 36/2021: Pengupahan, THR, Overtime, Min wage structure
- PP 37/2021: JKP (0.46%, 6 months benefit)
- PP 51/2023: UMP/UMK formula
- PP 34/2021: TKA, RPTKA requirements
- PP 44/2015: JKK (0.24-1.74%) + JKM (0.30%)
- PP 45/2015: JP (3%: employer 2% + worker 1%)
- PP 46/2015: JHT (5.7%: employer 3.7% + worker 2%)
- Perpres 64/2020 jo. 19/2024: BPJS Kesehatan (5%: employer 4% + worker 1%)
- UU 13/2003: Ketenagakerjaan
- UU 2/2004: PHI dispute resolution
- UU 6/2023: Cipta Kerja
- UMP 2025: 38 provinces"""


def call_llm_chat(messages: list[dict]) -> dict | None:
    import anthropic

    api_key, base_url, model = get_llm_config()
    if not api_key:
        return None

    try:
        client = anthropic.Anthropic(api_key=api_key, base_url=base_url)

        api_messages = [{"role": "user", "content": f"{SYSTEM_PROMPT}\n\n{messages[0]['content']}"}]
        for msg in messages[1:]:
            api_messages.append({"role": msg["role"], "content": msg["content"]})

        response = client.messages.create(
            model=model,
            max_tokens=2048,
            timeout=120.0,
            messages=api_messages,
        )

        raw = None
        if response.content:
            raw = response.content[0].text
        else:
            d = response.to_dict() if hasattr(response, 'to_dict') else {}
            choices = d.get('choices')
            if choices:
                raw = choices[0]['message']['content']

        if not raw:
            return None

        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()

        return json.loads(raw)
    except (json.JSONDecodeError, Exception):
        return None


def call_llm_simple(prompt: str) -> str | None:
    import anthropic

    api_key, base_url, model = get_llm_config()
    if not api_key:
        return None

    try:
        client = anthropic.Anthropic(api_key=api_key, base_url=base_url)
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            timeout=120.0,
            messages=[{"role": "user", "content": prompt}],
        )

        if response.content:
            return response.content[0].text
        d = response.to_dict() if hasattr(response, 'to_dict') else {}
        choices = d.get('choices')
        if choices:
            return choices[0]['message']['content']
        return None
    except Exception:
        return None


def _openai_base_url(base_url: str) -> str:
    """Ensure base_url ends with /v1 exactly once."""
    return base_url.rstrip("/") + "/v1" if not base_url.rstrip("/").endswith("/v1") else base_url.rstrip("/")


def stream_llm_chat(messages: list[dict]):
    """Generator that yields text tokens from the LLM. OpenAI-compatible gateway."""
    import openai

    api_key, base_url, model = get_llm_config()
    if not api_key:
        return

    try:
        client = openai.OpenAI(api_key=api_key, base_url=_openai_base_url(base_url))

        api_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in messages:
            api_messages.append({"role": msg["role"], "content": msg["content"]})

        stream = client.chat.completions.create(
            model=model,
            max_tokens=2048,
            messages=api_messages,
            stream=True,
        )

        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception:
        return


async def async_stream_llm_chat(messages: list[dict]):
    """Async generator that yields text tokens. OpenAI-compatible gateway."""
    import openai

    api_key, base_url, model = get_llm_config()
    if not api_key:
        return

    try:
        client = openai.AsyncOpenAI(api_key=api_key, base_url=_openai_base_url(base_url))

        api_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in messages:
            api_messages.append({"role": msg["role"], "content": msg["content"]})

        stream = await client.chat.completions.create(
            model=model,
            max_tokens=2048,
            messages=api_messages,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception:
        return
