"""LLM service — Anthropic client wrapper."""

from __future__ import annotations

import json
import os
from pathlib import Path


def _load_env():
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())


_load_env()

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
BASE_URL = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")


SYSTEM_PROMPT = """You are an Indonesian HR compliance assistant backed by a legal knowledge graph with 17 parsed regulations and 5,676 provisions.

RESPONSE FORMAT — return JSON:
{
  "hukum": [{"description": "fact + citation", "legal_basis": "PP/2021/35/Bab/II/Pasal/8", "severity": "high"}],
  "analisis": "interpretation text or null",
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
- hukum: ONLY graph-backed facts with Pasal citation. If you can't cite it, put in analisis.
- analisis: Your reasoning/advice. Always labeled as interpretation.
- perlu_dikonfirmasi: Structured questions when critical info is missing.
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

    if not API_KEY:
        return None

    try:
        client = anthropic.Anthropic(api_key=API_KEY, base_url=BASE_URL)

        api_messages = [{"role": "user", "content": f"{SYSTEM_PROMPT}\n\n{messages[0]['content']}"}]
        for msg in messages[1:]:
            api_messages.append({"role": msg["role"], "content": msg["content"]})

        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            timeout=120.0,
            messages=api_messages,
        )

        raw = response.content[0].text if response.content else None
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

    if not API_KEY:
        return None

    try:
        client = anthropic.Anthropic(api_key=API_KEY, base_url=BASE_URL)
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            timeout=120.0,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text if response.content else None
    except Exception:
        return None
