# Backend Specification — HR Compliance Redesign

> This document describes the **existing, frozen** backend API. It is the canonical reference for the frontend rewrite.

---

## 1. Feature Summary

The backend provides an Indonesian HR compliance checking system powered by:

- **Knowledge Graph**: Neo4j database with 17 Indonesian labor regulations and 5,676 provisions
- **LLM Streaming**: OpenAI-compatible gateway for structured legal analysis with progressive SSE delivery
- **Compliance Pipeline**: Document upload → obligation matching → scorecard (deterministic YAML engine)
- **Severance Calculator**: Statutory formula computation per PP 35/2021
- **Provision Lookup**: Direct graph queries for citation drill-down
- **Auth**: Env-based bearer token with in-memory session store

The frontend redesign consumes these APIs without modification. All conversation state is client-side (IndexedDB); the backend maintains only ephemeral per-session LLM context.

---

## 2. Data Model (Canonical Schemas)

All models defined in `backend/schemas.py` as Pydantic `BaseModel`.

### 2.1 Chat Domain

```python
class ChatAttachment(BaseModel):
    filename: str
    content_type: str
    data_base64: str

class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str
    attachments: list[ChatAttachment] | None = None
    context: dict | None = None

class HukumItem(BaseModel):
    description: str
    legal_basis: str              # node_id format: "PP/2021/35/Bab/II/Pasal/8"
    severity: str = "medium"      # "high" | "medium" | "low"
    legal_text_summary: str | None = None
    doc_evidence: str | None = None

class PerluDikonfirmasiItem(BaseModel):
    question: str
    why: str = ""
    options: list[str] | None = None
    parameter_key: str = ""
    type: str = "text"            # "select" | "number" | "text" | "file"

class ActionItem(BaseModel):
    description: str
    severity: str = "high"
    legal_basis: str = ""

class AnalisisBlock(BaseModel):
    text: str
    disclaimer: str = "Interpretasi — bukan hukum. Hasil di pengadilan bisa berbeda."

class ChatResponseBody(BaseModel):
    response_type: str = "chat"   # "chat" | "compliance_report"
    hukum: list[HukumItem] = []
    analisis: AnalisisBlock | None = None
    perlu_dikonfirmasi: list[PerluDikonfirmasiItem] = []
    actions: list[ActionItem] = []
    quick_actions: list[dict] | None = None
    # Compliance report fields (only when response_type = "compliance_report")
    compliance_score: int | None = None
    compliance_doc_type: str | None = None
    compliance_summary: dict | None = None  # {compliant: int, violated: int, not_evaluated: int}

class ChatResponse(BaseModel):
    session_id: str
    response: ChatResponseBody
```

### 2.2 Severance Calculator

```python
class SeveranceRequest(BaseModel):
    masa_kerja_bulan: int
    upah_pokok: int
    tunjangan_tetap: int = 0
    alasan_phk: str               # TerminationReason enum value
    tanggal_phk: str | None = None

class SeveranceComponent(BaseModel):
    amount: int
    formula: str
    multiplier: float | None = None

class SeveranceResponse(BaseModel):
    pesangon: SeveranceComponent
    penghargaan: SeveranceComponent
    penggantian_hak: SeveranceComponent
    total: int
    legal_basis: list[dict]       # [{pasal: str, description: str}]
    comparison: dict | None = None
```

### 2.3 Provision Lookup

```python
class ProvisionChild(BaseModel):
    node_id: str
    type: str
    number: str
    text_preview: str | None = None

class ProvisionResponse(BaseModel):
    node_id: str
    type: str
    number: str
    text: str | None = None
    parent: str | None = None
    children: list[ProvisionChild] = []
    regulation: dict | None = None
    norms_derived: list[dict] = []  # [{id: str, description: str, severity: str}]
```

### 2.4 Compliance Check

```python
class ComplianceCheckRequest(BaseModel):
    context: dict
    document: ChatAttachment | None = None

class ComplianceCheckResult(BaseModel):
    norm_id: str
    norm_description: str
    status: str                   # "pass" | "violation" | "unknown" | "warning"
    severity: str
    detail: str
    legal_basis: str
    evidence_needed: str | None = None
    edge_case: str | None = None

class ComplianceCheckResponse(BaseModel):
    summary: dict                 # {passed: int, warnings: int, violations: int}
    results: list[ComplianceCheckResult]
```

### 2.5 Explain

```python
class ExplainDefinition(BaseModel):
    node_id: str
    text: str

class ExplainResponse(BaseModel):
    term: str
    definition: str
    explanation: str | None = None
    sources: list[ExplainDefinition] = []
    key_points: list[str] = []
```

### 2.6 Auth (inline models in route)

```python
class LoginRequest(BaseModel):
    username: str
    password: str
```

### 2.7 Settings (inline model in route)

```python
class SettingsUpdate(BaseModel):
    model: str | None = None
    base_url: str | None = None
```

---

## 3. API Endpoints

### 3.1 Health Check

| | |
|---|---|
| **Method** | `GET /health` |
| **Auth** | None (public) |
| **Response** | `{ "status": "ok" }` |

---

### 3.2 Authentication

#### POST /api/auth/login

| | |
|---|---|
| **Auth** | None (public) |
| **Request Body** | `{ "username": string, "password": string }` |
| **Success (200)** | `{ "token": string }` — 64-char hex token |
| **Error (401)** | `{ "detail": "Invalid credentials" }` |
| **Error (429)** | `{ "detail": "Too many attempts. Try again later." }` |
| **Error (500)** | `{ "detail": "Auth not configured" }` |

Token is valid for 7 days (604,800 seconds). Rate limited to 5 attempts per IP per 5-minute window.

#### GET /api/auth/check

| | |
|---|---|
| **Auth** | None (public path, but validates the Bearer token in header) |
| **Header** | `Authorization: Bearer {token}` |
| **Success (200)** | `{ "ok": true }` |
| **Error (401)** | `{ "detail": "Unauthorized" }` |

---

### 3.3 Chat (Non-Streaming)

#### POST /api/chat

| | |
|---|---|
| **Auth** | Bearer token |
| **Request Body** | `ChatRequest` |
| **Response** | `ChatResponse` |

Business logic:
1. Creates/reuses session by `session_id`
2. Extracts text from any base64 attachments (PDF via pymupdf, TXT direct)
3. Detects conceptual questions → injects graph definitions into LLM context
4. Calls LLM (non-streaming, Anthropic SDK)
5. Post-validates citations against Neo4j (demotes invalid hukum to analisis)
6. Gates `perlu_dikonfirmasi` by intent (`severance_calc`, `ump_check` only)

---

### 3.4 Chat Streaming (V1 — Legacy)

#### POST /api/chat/stream

| | |
|---|---|
| **Auth** | Bearer token |
| **Request Body** | `ChatRequest` |
| **Response** | `text/event-stream` (SSE) |

SSE event format:
```
data: {"type": "status", "text": "Memproses..."}\n\n
data: {"type": "status", "text": "Menganalisis..."}\n\n
data: {"type": "text", "delta": "..."}\n\n          # analisis tokens
data: {"type": "complete", "data": {...}, "session_id": "..."}\n\n
data: [DONE]\n\n
```

The `complete` event contains the full parsed JSON response (same shape as LLM output). Intent gating applied to `perlu_dikonfirmasi`.

---

### 3.5 Chat Streaming (V2 — Primary)

#### POST /api/chat/stream-v2

| | |
|---|---|
| **Auth** | Bearer token |
| **Request Body** | `ChatRequest` |
| **Response** | `text/event-stream` (SSE) |

Progressive typed events — each independently renderable:

```
data: {"type":"status","data":{"text":"Memproses..."}}\n\n
data: {"type":"status","data":{"text":"Menganalisis..."}}\n\n
data: {"type":"hukum_item","data":{"description":"...","legal_basis":"...","severity":"..."}}\n\n
data: {"type":"analisis_delta","delta":"..."}\n\n
data: {"type":"perlu_item","data":{"question":"...","why":"...","options":[],"key":"...","type":"..."}}\n\n
data: {"type":"action_item","data":{"description":"...","severity":"...","legal_basis":"..."}}\n\n
data: {"type":"done","data":{"session_id":"..."}}\n\n
data: [DONE]\n\n
```

On error during streaming:
```
data: {"type":"error","data":{"text":"LLM error: ..."}}\n\n
data: [DONE]\n\n
```

Business logic:
1. IncrementalParser state machine parses JSON tokens as they arrive
2. `hukum_item` emitted as each object closes in the `hukum` array
3. `analisis_delta` emitted as text tokens stream within the `analisis` string (unescaped)
4. `perlu_item` events are **buffered** and only emitted after full response if intent is in `{severance_calc, ump_check}`
5. `action_item` emitted as each object closes in the `actions` array
6. Definition context injection for conceptual questions (same as non-streaming)
7. Session history appended after stream completes

**[ASSUMED: V2 does NOT perform citation validation — unlike the non-streaming /api/chat endpoint. Citations arrive as-is from LLM.]**

---

### 3.6 Document Upload

#### POST /api/chat/upload

| | |
|---|---|
| **Auth** | Bearer token |
| **Content-Type** | `multipart/form-data` |
| **Fields** | `file` (binary, required), `message` (string, default "Analisis dokumen ini"), `session_id` (string, default "") |
| **Response** | `ChatResponse` |

Business logic:
1. Extracts text from uploaded file (PDF/TXT, max 8000 chars)
2. Runs deterministic compliance pipeline (`run_compliance_pipeline`)
3. If pipeline matches a known doc type: returns `response_type: "compliance_report"` with score, violations, actions
4. If pipeline fails to match: falls back to LLM chat analysis
5. Compliance report includes `compliance_score` (0-100), `compliance_doc_type`, `compliance_summary`

---

### 3.7 Provision Lookup

#### GET /api/provision/{node_id}

| | |
|---|---|
| **Auth** | Bearer token |
| **Path Param** | `node_id` — full provision path (e.g., `PP/2021/35/Bab/II/Pasal/8`). URL-encoded slashes. |
| **Success (200)** | `ProvisionResponse` |
| **Error (404)** | `{ "detail": "Provision not found" }` |

The route uses `{node_id:path}` capture (FastAPI path converter) — accepts embedded slashes without encoding.

Lookup strategy:
1. Exact match on `node_id`
2. Fuzzy match: strips Bab segment, matches on regulation prefix + Pasal suffix

Text is cleaned (PDF line-break normalization, whitespace collapse).

---

### 3.8 Severance Calculator

#### POST /api/calculate/severance

| | |
|---|---|
| **Auth** | Bearer token |
| **Request Body** | `SeveranceRequest` |
| **Response** | `SeveranceResponse` |

Business logic:
1. Converts `masa_kerja_bulan` to years (integer division by 12)
2. Sums `upah_pokok + tunjangan_tetap` as salary base
3. Maps `alasan_phk` to `TerminationReason` enum (defaults to `EFFICIENCY_CLOSURE` on invalid)
4. Calls deterministic `calculate_severance(years, salary, reason)`
5. Returns itemized components with formulas and legal basis citations

---

### 3.9 Settings

#### GET /api/settings

| | |
|---|---|
| **Auth** | Bearer token |
| **Response** | `{ "model": string, "base_url": string }` |

#### POST /api/settings

| | |
|---|---|
| **Auth** | Bearer token |
| **Request Body** | `SettingsUpdate` — `{ "model"?: string, "base_url"?: string }` |
| **Response** | `{ "model": string, "base_url": string }` |

Partial updates supported. Writes to `data/.settings.json`.

#### GET /api/settings/models

| | |
|---|---|
| **Auth** | Bearer token |
| **Response** | `{ "models": string[] }` |

Fetches model list from the configured gateway's `/v1/models` endpoint. Returns empty array on failure (no error propagated). Timeout: 10 seconds.

---

### 3.10 Compliance Check (Programmatic)

#### POST /api/compliance/check

| | |
|---|---|
| **Auth** | Bearer token |
| **Request Body** | `ComplianceCheckRequest` — `{ "context": dict, "document"?: ChatAttachment }` |
| **Response** | `ComplianceCheckResponse` |

Runs the deterministic obligation engine against structured fields. The `context.contract_type` field determines which `DocType` rule set to apply (default: `pkwt`).

---

### 3.11 Explain (Term Lookup)

#### GET /api/explain?term={term}

| | |
|---|---|
| **Auth** | Bearer token |
| **Query Param** | `term` (min 2 chars, required) |
| **Response** | `ExplainResponse` |

Business logic:
1. Expands known abbreviations (PKWT, PHK, UMP, etc.) to search keywords
2. Searches graph for definition provisions (prioritizes Pasal 1 / "Ketentuan Umum")
3. Sends provision text to LLM for structured explanation
4. Falls back to raw provision text if LLM unavailable

---

## 4. Business Rules Catalog

### 4.1 Intent Gating (PRD 3.6: Quick Actions/Follow-Ups)

`perlu_dikonfirmasi` items are **only emitted** when the LLM's declared `intent` is one of:
- `severance_calc` — severance calculation needing salary/tenure inputs
- `ump_check` — minimum wage comparison needing province

All other intents (`general_hr`, `pkwt`, `phi_dispute`, `bpjs_rates`) have `perlu_dikonfirmasi` suppressed to zero. This prevents the LLM from asking unnecessary clarification questions.

Applied in: `/api/chat`, `/api/chat/stream`, `/api/chat/stream-v2`.

### 4.2 Citation Validation (PRD 3.3: Citation Panel)

Non-streaming `/api/chat` only:
1. All `hukum` items must have a `legal_basis` containing `/Pasal/`
2. Each `legal_basis` is checked against Neo4j (exact + fuzzy match)
3. Items failing validation are **demoted** — their `description` is appended to `analisis.text` as bullet points
4. This ensures every hukum item in the response is graph-backed and clickable

**[OPEN: V2 streaming does NOT perform citation validation. Should the frontend filter client-side, or is this accepted as-is?]**

### 4.3 Definition Context Injection (PRD 3.1: Streaming Chat)

When a user message matches conceptual question patterns:
- Pattern matching: "apa itu X", "what is X", "definisi X", "jelaskan X", bare abbreviations ("PKWT?")
- Known abbreviations auto-expanded (14 terms: PKWT, PKWTT, PHK, UMP, UMK, THR, BPJS, JHT, JKK, JKM, JP, JKP, TKA, alih daya, lembur, cuti, pesangon)
- Graph search for definition provisions (prioritizes Pasal 1, "yang dimaksud dengan")
- Up to 6 definitions (400 chars each) appended to user message as hidden context

This happens transparently — the frontend sends a normal message; the backend enriches it before LLM call.

### 4.4 Rate Limiting (Auth)

Login endpoint only:
- 5 attempts per IP per 300-second window
- Counter resets on successful login
- Returns 429 when exceeded

No rate limiting on other endpoints.

### 4.5 Auth Middleware

Global HTTP middleware on all paths except `{/health, /api/auth/login, /api/auth/check}`:
- If `AUTH_USER` env var is not set → auth disabled entirely (all requests pass)
- If set → requires `Authorization: Bearer {token}` header with valid, non-expired token
- Returns 401 JSON on failure

### 4.6 Session Memory

In-memory `dict[str, list[dict]]` per endpoint module:
- `/api/chat` and `/api/chat/stream` share one session store
- `/api/chat/stream-v2` has its own independent session store
- Sessions are keyed by `session_id` (UUID generated if not provided)
- History grows unbounded within a process lifetime
- Lost on server restart

**[OPEN: The two session stores are independent. A session started on /chat/stream-v2 has no history visible to /chat or /chat/stream. Frontend should use V2 exclusively.]**

### 4.7 Document Text Extraction

- PDF: pymupdf, full text extraction, capped at 8,000 characters
- TXT: UTF-8 decode (Latin-1 fallback), capped at 8,000 characters
- Other formats: metadata string only (`[File: name, N bytes]`)
- Scanned/image-based PDFs return `[PDF is scanned/image-based]`

---

## 5. Side Effects Map

| Trigger | Side Effect | Persistence |
|---------|-------------|-------------|
| Any chat request | Session history appended (in-memory) | Process lifetime only |
| `/api/chat` | LLM call (Anthropic SDK, non-streaming) | None |
| `/api/chat` | Neo4j read: `validate_citations` (per hukum item) | None |
| `/api/chat/stream-v2` | LLM call (OpenAI SDK, streaming) | None |
| `/api/chat/stream-v2` | Neo4j read: `search_definitions` (if conceptual) | None |
| `/api/chat/upload` | File read into memory (full content) | None |
| `/api/chat/upload` | Compliance pipeline execution (deterministic) | None |
| `/api/chat/upload` | LLM call (fallback if pipeline fails) | None |
| `/api/provision/{id}` | Neo4j read: node + children + norms | None |
| `/api/explain` | Neo4j read: `search_definitions` | None |
| `/api/explain` | LLM call (`call_llm_simple`) | None |
| `/api/compliance/check` | Compliance pipeline evaluation (deterministic) | None |
| `/api/calculate/severance` | Pure computation (no external calls) | None |
| `POST /api/settings` | File write: `data/.settings.json` | Disk |
| `POST /api/auth/login` | Token stored in-memory dict | Process lifetime |
| `POST /api/auth/login` | Rate limit counter updated | Process lifetime |
| `GET /api/settings/models` | HTTP GET to gateway `/v1/models` | None |

---

## 6. Error Taxonomy

### 6.1 HTTP Status Codes

| Code | Condition | Response Shape |
|------|-----------|----------------|
| 200 | Success | Endpoint-specific |
| 401 | Missing/invalid/expired token | `{ "detail": "Unauthorized" }` |
| 401 | Invalid login credentials | `{ "detail": "Invalid credentials" }` |
| 404 | Provision not found in graph | `{ "detail": "Provision not found" }` |
| 422 | Pydantic validation failure (FastAPI) | `{ "detail": [{"loc": [...], "msg": "...", "type": "..."}] }` |
| 429 | Login rate limit exceeded | `{ "detail": "Too many attempts. Try again later." }` |
| 500 | Auth env vars not configured | `{ "detail": "Auth not configured" }` |

### 6.2 SSE Error Events (stream-v2)

| Condition | Event |
|-----------|-------|
| LLM call raises exception | `{"type":"error","data":{"text":"LLM error: {ExceptionType}: {message}"}}` |
| Zero tokens received | `{"type":"error","data":{"text":"No tokens received from LLM"}}` |

After an error event, `data: [DONE]\n\n` is always sent to close the stream.

### 6.3 SSE Error Events (stream v1)

On exception during streaming, emits a `complete` event with fallback data:
```json
{"type": "complete", "data": {"analisis": "Tidak dapat memproses.", "hukum": []}, "session_id": "..."}
```

### 6.4 Graceful Degradation

| Service Down | Behavior |
|--------------|----------|
| Neo4j unavailable | `get_provision` returns None (404), `validate_citations` returns all-false, `search_definitions` returns empty |
| LLM unavailable (no API key) | `/api/chat` returns generic error analisis, streaming yields no tokens → error event |
| Gateway /models unreachable | `/api/settings/models` returns `{ "models": [] }` |
| Compliance pipeline no match | `/api/chat/upload` falls back to LLM analysis |

---

## 7. Performance and Scaling

### 7.1 Hot Paths

| Path | Latency Profile | Bottleneck |
|------|----------------|------------|
| `/api/chat/stream-v2` | 2-30s (LLM dependent) | LLM token generation |
| `/api/chat` | 5-30s (blocking) | LLM completion |
| `/api/chat/upload` | 5-60s | Text extraction + compliance pipeline + potential LLM fallback |
| `/api/provision/{id}` | 10-100ms | Neo4j query (2 queries for fuzzy) |
| `/api/calculate/severance` | <5ms | Pure computation |
| `/api/settings/models` | 0-10s | External HTTP to gateway |
| `/api/explain` | 5-30s | Graph search + LLM call |

### 7.2 Streaming Behavior

- SSE with `text/event-stream` media type
- Headers: `Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no` (nginx proxy compatibility)
- IncrementalParser processes tokens one-at-a-time via state machine — no buffering delay for `hukum_item` and `analisis_delta`
- `perlu_item` events are intentionally buffered until stream completion (intent gating requires full response)
- Stream terminates with `data: [DONE]\n\n` sentinel

### 7.3 Concurrency Model

- FastAPI async (uvicorn) — single process assumed for Docker deployment
- LLM streaming uses `openai.AsyncOpenAI` (non-blocking)
- Non-streaming LLM calls use synchronous `anthropic.Anthropic` (blocks the event loop)
- Neo4j driver: synchronous session per call (brief blocking)
- In-memory session dicts are not thread-safe but acceptable for single-worker deployment

**[OPEN: Under concurrent requests, the synchronous Anthropic SDK calls in /api/chat will block the event loop. For 5-10 users this is likely acceptable but could cause head-of-line blocking under load.]**

### 7.4 Memory Characteristics

- Session history: unbounded growth (no eviction, no max-length)
- Token store: entries removed on expiry check (lazy eviction)
- Rate limit store: cleaned on each check (sliding window)
- No disk caching of provisions or LLM responses

---

## 8. Acceptance Criteria

### Auth

- [ ] `POST /api/auth/login` with correct credentials returns `{ "token": <64-char hex> }`
- [ ] `POST /api/auth/login` with wrong credentials returns 401
- [ ] 6th failed login from same IP within 5 minutes returns 429
- [ ] `GET /api/auth/check` with valid token returns `{ "ok": true }`
- [ ] `GET /api/auth/check` with expired token (>7 days) returns 401
- [ ] Any protected endpoint without Authorization header returns 401
- [ ] When `AUTH_USER` env is unset, all endpoints are accessible without token

### Chat Stream V2

- [ ] `POST /api/chat/stream-v2` returns `Content-Type: text/event-stream`
- [ ] First event is `status` with text "Memproses..."
- [ ] Second event is `status` with text "Menganalisis..." (after first LLM token)
- [ ] `hukum_item` events contain valid `HukumItem` shape
- [ ] `analisis_delta` events contain incremental text (unescaped newlines, quotes)
- [ ] `perlu_item` events are only emitted when intent is `severance_calc` or `ump_check`
- [ ] `action_item` events contain valid `ActionItem` shape
- [ ] Stream always terminates with `done` event followed by `data: [DONE]\n\n`
- [ ] On LLM error, `error` event is emitted before `[DONE]`
- [ ] Session ID is returned in `done` event (generated UUID if not provided)
- [ ] Conceptual question ("apa itu PKWT") triggers definition context injection

### Document Upload

- [ ] `POST /api/chat/upload` accepts multipart with `file`, `message`, `session_id` fields
- [ ] PDF file returns compliance report with `response_type: "compliance_report"`
- [ ] Compliance report includes `compliance_score`, `compliance_doc_type`, `compliance_summary`
- [ ] Unknown document type falls back to LLM analysis with `response_type: "chat"`
- [ ] `message` field defaults to "Analisis dokumen ini" when omitted

### Provision Lookup

- [ ] `GET /api/provision/PP/2021/35/Bab/V/Pasal/40` returns provision with children and norms
- [ ] Non-existent node_id returns 404
- [ ] Fuzzy match works: omitting Bab segment still finds the Pasal
- [ ] Response text is cleaned (no raw PDF line breaks)
- [ ] `children[].text_preview` is capped at 100 chars

### Calculator

- [ ] `POST /api/calculate/severance` with valid input returns itemized breakdown
- [ ] Each component has `amount` (int), `formula` (human-readable string)
- [ ] `pesangon` component includes `multiplier` field
- [ ] Invalid `alasan_phk` defaults to `EFFICIENCY_CLOSURE` (no error)
- [ ] `legal_basis` array contains at least 2 entries

### Settings

- [ ] `GET /api/settings` returns current `{ "model", "base_url" }`
- [ ] `POST /api/settings` with `{ "model": "x" }` updates model only, preserves base_url
- [ ] `GET /api/settings/models` returns sorted model ID list from gateway
- [ ] `GET /api/settings/models` returns `{ "models": [] }` when gateway unreachable

### Compliance Check

- [ ] `POST /api/compliance/check` with `context.contract_type: "pkwt"` evaluates PKWT obligations
- [ ] Response `summary` has `passed`, `warnings`, `violations` counts
- [ ] Each result has `norm_id`, `status`, `severity`, `legal_basis`

### Explain

- [ ] `GET /api/explain?term=PKWT` returns definition sourced from graph
- [ ] Response includes `sources` array with node_ids
- [ ] Term shorter than 2 chars returns 422
- [ ] When LLM unavailable, returns raw provision text as fallback
