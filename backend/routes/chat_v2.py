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
import uuid
from enum import Enum, auto

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ..schemas import ChatRequest
from ..services.llm import async_stream_llm_chat

router = APIRouter()


class State(Enum):
    SCANNING = auto()
    IN_HUKUM_ARRAY = auto()
    IN_ANALISIS_STRING = auto()
    IN_PERLU_ARRAY = auto()
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
        self.buffer += token

        if self.state == State.SCANNING:
            self._scan()
        elif self.state == State.IN_HUKUM_ARRAY:
            self._parse_array("hukum_item")
        elif self.state == State.IN_ANALISIS_STRING:
            self._parse_string()
        elif self.state == State.IN_PERLU_ARRAY:
            self._parse_array("perlu_item")

        return self.events

    def _scan(self):
        markers = [
            ('"hukum"', State.IN_HUKUM_ARRAY),
            ('"analisis"', State.IN_ANALISIS_STRING),
            ('"perlu_dikonfirmasi"', State.IN_PERLU_ARRAY),
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
                self._parse_array("hukum_item" if next_state == State.IN_HUKUM_ARRAY else "perlu_item")
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


@router.post("/chat/stream-v2")
async def chat_stream_v2(req: ChatRequest):
    from ..services.llm import SYSTEM_PROMPT
    from ..services.graph import search_definitions

    session_id = req.session_id or str(uuid.uuid4())

    messages = [{"role": "user", "content": req.message}]

    async def generate():
        yield _sse("status", {"text": "Memproses..."})

        parser = IncrementalParser()
        token_count = 0

        try:
            async for token in async_stream_llm_chat(messages):
                token_count += 1
                if token_count == 1:
                    yield _sse("status", {"text": "Menganalisis..."})

                events = parser.feed(token)
                for event_type, data in events:
                    yield _sse(event_type, data)

        except Exception:
            yield _sse("error", {"text": "Tidak dapat memproses."})
            yield "data: [DONE]\n\n"
            return

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
