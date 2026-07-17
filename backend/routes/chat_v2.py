"""Progressive streaming endpoint — /api/chat/stream-v2

State machine that emits typed SSE events per semantic unit:
- hukum_item: each hukum object as it closes
- analisis_delta: text tokens from the analisis field
- perlu_item: each perlu_dikonfirmasi object as it closes
- done: signals end of response

No post-hoc JSON surgery. Each event is independently renderable.
"""

from __future__ import annotations

import json
import re
import uuid
from enum import Enum, auto
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..schemas import ChatRequest
from ..services.llm import async_stream_llm_chat, get_llm_config, SYSTEM_PROMPT, _openai_base_url

router = APIRouter()

_sessions: dict[str, list[dict]] = {}


class State(Enum):
    SCANNING = auto()
    IN_HUKUM_ARRAY = auto()
    IN_ANALISIS_STRING = auto()
    IN_PERLU_ARRAY = auto()
    IN_ACTIONS_ARRAY = auto()
    TAIL = auto()


def _sse(event_type: str, data: dict | str) -> str:
    payload = {"type": event_type}
    if isinstance(data, str):
        payload["delta"] = data
    else:
        payload["data"] = data
    return f"data: {json.dumps(payload)}\n\n"


class IncrementalParser:
    """Schema-aware incremental JSON parser for our known response format.

    Expects: {"hukum": [...], "analisis": "...", "perlu_dikonfirmasi": [...], ...}
    Emits events as each semantic unit completes.
    """

    def __init__(self):
        self.state = State.SCANNING
        self.buffer = ""
        self.brace_depth = 0
        self.item_buffer = ""
        self.analisis_buffer = ""
        self.last_analisis_len = 0
        self.events: list[tuple[str, dict | str]] = []

    def feed(self, token: str) -> list[tuple[str, dict | str]]:
        self.events = []

        if self.state == State.IN_ANALISIS_STRING:
            self.analisis_buffer += token
        else:
            self.buffer += token

        if self.state == State.SCANNING:
            self._scan()
        elif self.state == State.IN_HUKUM_ARRAY:
            self._parse_array("hukum_item")
        elif self.state == State.IN_ANALISIS_STRING:
            self._parse_string()
        elif self.state == State.IN_PERLU_ARRAY:
            self._parse_array("perlu_item")
        elif self.state == State.IN_ACTIONS_ARRAY:
            self._parse_array("action_item")

        return self.events

    def _scan(self):
        markers = [
            ('"hukum"', State.IN_HUKUM_ARRAY),
            ('"analisis"', State.IN_ANALISIS_STRING),
            ('"perlu_dikonfirmasi"', State.IN_PERLU_ARRAY),
            ('"actions"', State.IN_ACTIONS_ARRAY),
        ]
        for marker, next_state in markers:
            idx = self.buffer.find(marker)
            if idx == -1:
                continue

            after_key = self.buffer[idx + len(marker):]
            colon_idx = after_key.find(":")
            if colon_idx == -1:
                continue

            after_colon = after_key[colon_idx + 1:].lstrip()
            if not after_colon:
                continue

            if next_state == State.IN_ANALISIS_STRING:
                quote_idx = after_colon.find('"')
                if quote_idx == -1:
                    continue
                self.state = next_state
                self.analisis_buffer = after_colon[quote_idx + 1:]
                self.last_analisis_len = 0
                self.buffer = ""
                self._parse_string()
                return
            else:
                bracket_idx = after_colon.find("[")
                if bracket_idx == -1:
                    continue
                self.state = next_state
                self.buffer = after_colon[bracket_idx + 1:]
                self.brace_depth = 0
                self.item_buffer = ""
                event_name = {
                    State.IN_HUKUM_ARRAY: "hukum_item",
                    State.IN_PERLU_ARRAY: "perlu_item",
                    State.IN_ACTIONS_ARRAY: "action_item",
                }[next_state]
                self._parse_array(event_name)
                return

    def _parse_array(self, event_type: str):
        i = 0
        while i < len(self.buffer):
            c = self.buffer[i]

            if c == "]" and self.brace_depth == 0:
                self.state = State.SCANNING
                self.buffer = self.buffer[i + 1:]
                self._scan()
                return

            if c == "{":
                self.brace_depth += 1
                self.item_buffer += c
            elif c == "}" and self.brace_depth > 0:
                self.brace_depth -= 1
                self.item_buffer += c
                if self.brace_depth == 0:
                    try:
                        item = json.loads(self.item_buffer)
                        self.events.append((event_type, item))
                    except json.JSONDecodeError:
                        pass
                    self.item_buffer = ""
            elif self.brace_depth > 0:
                self.item_buffer += c
            i += 1

        self.buffer = ""

    def _parse_string(self):
        text = self.analisis_buffer
        result = []
        i = 0
        consumed = 0

        while i < len(text):
            c = text[i]
            if c == "\\":
                if i + 1 >= len(text):
                    break  # incomplete escape, wait
                nc = text[i + 1]
                if nc == "n":
                    result.append("\n")
                elif nc == '"':
                    result.append('"')
                elif nc == "\\":
                    result.append("\\")
                elif nc == "t":
                    result.append("\t")
                elif nc == "/":
                    result.append("/")
                else:
                    result.append(nc)
                i += 2
                consumed = i
            elif c == '"':
                consumed = i + 1
                self.state = State.SCANNING
                self.buffer = text[consumed:]
                full = "".join(result)
                if len(full) > self.last_analisis_len:
                    self.events.append(("analisis_delta", full[self.last_analisis_len:]))
                    self.last_analisis_len = len(full)
                self.analisis_buffer = ""
                self._scan()
                return
            else:
                result.append(c)
                i += 1
                consumed = i

        self.analisis_buffer = text[consumed:] if consumed < len(text) else text

        full = "".join(result)
        if len(full) > self.last_analisis_len:
            self.events.append(("analisis_delta", full[self.last_analisis_len:]))
            self.last_analisis_len = len(full)


async def _stream_llm(messages: list[dict]):
    """Stream LLM tokens without swallowing errors."""
    import openai

    api_key, base_url, model = get_llm_config()
    if not api_key:
        raise RuntimeError("No API key configured")

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


@router.post("/chat/stream-v2")
async def chat_stream_v2(req: ChatRequest):
    from ..services.graph import search_definitions
    from .chat import _detect_conceptual_question, _build_definition_context

    session_id = req.session_id or str(uuid.uuid4())

    if session_id not in _sessions:
        _sessions[session_id] = []

    _sessions[session_id].append({"role": "user", "content": req.message})

    # Inject definition context for conceptual questions
    definition_context = ""
    conceptual_keywords = _detect_conceptual_question(req.message)
    if conceptual_keywords:
        definition_context = _build_definition_context(conceptual_keywords)

    messages = _sessions[session_id][:]
    if definition_context and messages:
        messages[-1] = {
            "role": "user",
            "content": messages[-1]["content"] + definition_context,
        }

    async def generate():
        yield _sse("status", {"text": "Memproses..."})

        parser = IncrementalParser()
        token_count = 0
        buffered_perlu = []
        full_text = ""

        _INTENTS_THAT_NEED_INPUT = {"severance_calc", "ump_check"}

        try:
            async for token in _stream_llm(messages):
                token_count += 1
                full_text += token
                if token_count == 1:
                    yield _sse("status", {"text": "Menganalisis..."})

                events = parser.feed(token)
                for event_type, data in events:
                    if event_type == "perlu_item":
                        buffered_perlu.append(data)
                    else:
                        yield _sse(event_type, data)

        except Exception as e:
            yield _sse("error", {"text": f"LLM error: {type(e).__name__}: {e}"})
            yield "data: [DONE]\n\n"
            return

        if token_count == 0:
            yield _sse("error", {"text": "No tokens received from LLM"})

        # Gate perlu_dikonfirmasi by intent (only severance_calc and ump_check)
        intent = ""
        intent_match = full_text.find('"intent"')
        if intent_match != -1:
            after = full_text[intent_match:]
            m = re.search(r'"intent"\s*:\s*"([^"]*)"', after)
            if m:
                intent = m.group(1)

        if intent in _INTENTS_THAT_NEED_INPUT and buffered_perlu:
            for item in buffered_perlu:
                yield _sse("perlu_item", item)

        _sessions[session_id].append({"role": "assistant", "content": full_text})

        yield _sse("done", {"session_id": session_id})
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# AI SDK data stream protocol endpoint
# ---------------------------------------------------------------------------

class AIChatMessage(BaseModel):
    role: str
    content: str


class AIChatRequest(BaseModel):
    messages: list[AIChatMessage]


def _ai_evt(event_type: str, **kwargs: Any) -> str:
    payload = {"type": event_type, **kwargs}
    return f"data: {json.dumps(payload)}\n\n"


@router.post("/chat/ai")
async def chat_ai_stream(request: Request):
    from ..services.graph import search_definitions
    from .chat import _detect_conceptual_question, _build_definition_context

    body = await request.json()
    incoming_messages = body.get("messages", [])

    if not incoming_messages:
        return StreamingResponse(
            iter([_ai_evt("error", errorText="No messages provided"), "data: [DONE]\n\n"]),
            media_type="text/event-stream",
        )

    last_user_msg = ""
    for m in reversed(incoming_messages):
        if m.get("role") == "user":
            parts = m.get("parts", [])
            for p in parts:
                if p.get("type") == "text":
                    last_user_msg = p.get("text", "")
                    break
            if not last_user_msg:
                last_user_msg = m.get("content", "")
            break

    if not last_user_msg:
        return StreamingResponse(
            iter([_ai_evt("error", errorText="No user message found"), "data: [DONE]\n\n"]),
            media_type="text/event-stream",
        )

    session_id = str(uuid.uuid4())

    # Build conversation history for LLM
    history: list[dict] = []
    for m in incoming_messages:
        role = m.get("role", "user")
        parts = m.get("parts", [])
        content = ""
        for p in parts:
            if p.get("type") == "text":
                content += p.get("text", "")
        if not content:
            content = m.get("content", "")
        if content and role in ("user", "assistant"):
            history.append({"role": role, "content": content})

    # Inject definition context for conceptual questions
    conceptual_keywords = _detect_conceptual_question(last_user_msg)
    if conceptual_keywords:
        definition_context = _build_definition_context(conceptual_keywords)
        if history:
            history[-1] = {
                "role": history[-1]["role"],
                "content": history[-1]["content"] + definition_context,
            }

    message_id = str(uuid.uuid4())

    async def generate():
        yield _ai_evt("start", messageId=message_id)
        yield _ai_evt("start-step", messageId=message_id)

        parser = IncrementalParser()
        token_count = 0
        buffered_perlu: list[dict] = []
        full_text = ""

        _INTENTS_THAT_NEED_INPUT = {"severance_calc", "ump_check"}

        try:
            async for token in _stream_llm(history):
                token_count += 1
                full_text += token

                if token_count == 1:
                    yield _ai_evt("data-status", data={"text": "Menganalisis..."})

                events = parser.feed(token)
                for event_type, data in events:
                    if event_type == "hukum_item":
                        yield _ai_evt("data-hukum", data=data)
                    elif event_type == "analisis_delta":
                        yield _ai_evt("text-delta", textDelta=data)
                    elif event_type == "perlu_item":
                        buffered_perlu.append(data)
                    elif event_type == "action_item":
                        yield _ai_evt("data-action", data=data)

        except Exception as e:
            yield _ai_evt("error", errorText=f"LLM error: {type(e).__name__}: {e}")
            yield _ai_evt("finish-step", messageId=message_id)
            yield _ai_evt("finish", messageId=message_id)
            yield "data: [DONE]\n\n"
            return

        if token_count == 0:
            yield _ai_evt("error", errorText="No tokens received from LLM")

        # Gate perlu_dikonfirmasi by intent
        intent = ""
        intent_match = full_text.find('"intent"')
        if intent_match != -1:
            after = full_text[intent_match:]
            m = re.search(r'"intent"\s*:\s*"([^"]*)"', after)
            if m:
                intent = m.group(1)

        if intent in _INTENTS_THAT_NEED_INPUT and buffered_perlu:
            for item in buffered_perlu:
                yield _ai_evt("data-perlu", data=item)

        yield _ai_evt("finish-step", messageId=message_id,
                      metadata={"session_id": session_id})
        yield _ai_evt("finish", messageId=message_id)
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "x-vercel-ai-ui-message-stream": "v1",
        },
    )
