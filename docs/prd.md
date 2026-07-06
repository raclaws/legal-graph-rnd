# HR Compliance Frontend Redesign — Product Requirements Document

---

## 1. Intent

### Problem

The internal HR team uses a compliance tool daily to validate employment documents against Indonesian labor law, calculate severance, and answer legal questions. The current frontend was built as a research prototype (two chat pages testing different streaming approaches, minimal navigation, no workflow integration). It works, but it doesn't match how the team actually works:

- They re-ask the same questions weekly because there's no history or bookmarks.
- Switching between chat, calculator, and document upload requires context-switching with no state continuity.
- The citation sidebar accumulates items but offers no way to organize, export, or revisit them.
- There's no document management — uploads vanish after the session ends.
- Mobile access (checking answers in meetings) is essentially unusable.

### Audience

5-10 HR staff at a single Indonesian company. Non-lawyers who need clear verdicts, not raw legal text. They handle 5-20 compliance checks per week, frequently re-ask PKWT/severance/BPJS questions, work primarily in Bahasa Indonesia, and occasionally need mobile access during meetings.

### Success Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| Time-to-answer for repeated questions | < 10s (vs. current ~60s re-asking) | Session logs |
| Compliance check completion rate | > 90% (user finishes full scorecard review) | Frontend events |
| Mobile task completion | Core read flows usable on 375px viewport | Manual QA |
| Onboarding time for new HR staff | < 15 minutes to first compliance check | Observation |
| Page load (LCP) | < 1.5s on corporate network | Lighthouse |

### Constraints

- Backend API is frozen — no new endpoints, no schema changes.
- Auth mechanism stays as-is (env-based user/pass, bearer token, in-memory store).
- Neo4j graph is read-only from the frontend's perspective.
- LLM gateway is OpenAI-compatible; model is configurable but defaults to Claude Sonnet.
- Deployment: single Docker container (Vite build served by FastAPI static mount or Nginx).
- No external analytics or telemetry services — all metrics from application logs.
- Indonesian language UI (labels, placeholders, system messages).

---

## 2. Entities

### 2.1 Conversation

A chat thread between the user and the system.

**Attributes:**
- `id: string` — UUID, doubles as `session_id` sent to backend
- `title: string` — auto-generated from first message, editable
- `created_at: ISO datetime`
- `updated_at: ISO datetime`
- `pinned: boolean` — user can pin frequently-used conversations
- `messages: Message[]`

**Relationships:**
- Contains 1..N Messages
- May reference 0..N Citations (accumulated across messages)
- May reference 0..N Documents (attached during conversation)

**States:**
- `active` — currently open, streaming possible
- `archived` — soft-hidden from main list, still searchable

**[claude.md-ready]**

---

### 2.2 Message

A single turn in a conversation (user or assistant).

**Attributes:**
- `id: string` — local UUID
- `role: "user" | "assistant"`
- `content: string` — raw text (user) or structured response (assistant)
- `attachments: Attachment[]` — files sent with this message
- `response: StructuredResponse | null` — parsed assistant response (hukum, analisis, perlu, actions)
- `timestamp: ISO datetime`
- `status: MessageStatus`

**Relationships:**
- Belongs to exactly 1 Conversation
- May contain 0..N Attachments
- May produce 0..N Citations (from `hukum` items)

**States:**
- `sending` — user message in flight
- `streaming` — assistant response arriving via SSE
- `complete` — fully received and parsed
- `error` — stream failed, retryable

**[claude.md-ready]**

---

### 2.3 StructuredResponse

The parsed assistant response following the backend's JSON schema. Not a standalone entity — embedded in Message.

**Attributes:**
- `hukum: HukumItem[]` — legal basis cards
- `analisis: {text: string, disclaimer: string}` — analysis prose with `[n]` citation markers
- `perlu_dikonfirmasi: PerluItem[]` — follow-up questions (gated by intent)
- `actions: ActionItem[]` — remediation steps
- `quick_actions: string[]` — suggested follow-up prompts
- `intent: string` — classified intent
- `compliance_score: number | null` — 0-100 for document uploads
- `compliance_doc_type: string | null`
- `compliance_summary: string | null`

**[claude.md-ready]**

---

### 2.4 Citation

A legal reference extracted from a response, linked to a Neo4j provision.

**Attributes:**
- `node_id: string` — Neo4j path (e.g., `PP/2021/35/Bab/II/Pasal/8`)
- `description: string` — human summary from the hukum item
- `severity: "high" | "medium" | "low"`
- `legal_text_summary: string | null`
- `provision_detail: ProvisionDetail | null` — fetched on-demand from `/api/provision/{node_id}`

**Relationships:**
- Referenced by 1..N Messages (same citation can appear across messages)
- Belongs to the parent Conversation's citation set

**States:**
- `referenced` — appears in response, detail not yet fetched
- `expanded` — user clicked, provision detail loaded
- `bookmarked` — user explicitly saved for later reference

**[claude.md-ready]**

---

### 2.5 Document

A file uploaded for compliance analysis.

**Attributes:**
- `id: string` — local UUID
- `filename: string`
- `content_type: string`
- `size_bytes: number`
- `data_base64: string` — stored in-memory/IndexedDB for re-reference
- `uploaded_at: ISO datetime`
- `compliance_result: ComplianceResult | null`

**Relationships:**
- Attached to 1 Message (upload context)
- Belongs to 1 Conversation
- Produces 0..1 ComplianceResult

**States:**
- `pending` — uploaded, awaiting analysis
- `analyzed` — scorecard available
- `error` — analysis failed

**[claude.md-ready]**

---

### 2.6 ComplianceResult

The scorecard produced after document analysis.

**Attributes:**
- `score: number` — 0-100
- `doc_type: string` — detected document type
- `summary: string`
- `violations: ActionItem[]` — items with severity
- `compliant: ActionItem[]` — satisfied obligations
- `actions: ActionItem[]` — recommended remediation

**Relationships:**
- Produced by exactly 1 Document
- Contains 0..N ActionItems referencing Citations

**[claude.md-ready]**

---

### 2.7 CalculatorSession

A severance/pesangon calculation with inputs and result.

**Attributes:**
- `id: string`
- `inputs: SeveranceInputs` — `{years_of_service, monthly_salary, termination_reason, ...}`
- `result: SeveranceResult | null` — `{pesangon, penghargaan, penggantian, total, breakdown[]}`
- `created_at: ISO datetime`

**Relationships:**
- Standalone entity (no conversation link) [ASSUMED: calculator is independent of chat]
- May link to 0..N Citations (legal basis for calculation)

**States:**
- `draft` — inputs partially filled
- `calculated` — result available

**[claude.md-ready]**

---

### 2.8 UserPreferences

Per-user settings stored in localStorage.

**Attributes:**
- `language: "id"` — [ASSUMED: fixed to Indonesian for this team]
- `theme: "light" | "dark" | "system"`
- `citation_panel_open: boolean` — default sidebar state
- `pinned_conversations: string[]` — conversation IDs
- `bookmarked_citations: Citation[]`
- `recent_calculations: CalculatorSession[]` — last 10

**[claude.md-ready]**

---

## 3. Behavior

### 3.1 Streaming Chat

**Trigger:** User submits a message (text and/or file attachment) in an active conversation.

**Input:**
- `message: string` (required, non-empty)
- `attachments?: File[]` (optional, max 10MB per file, PDF/DOCX)
- `session_id: string` (the conversation's ID)

**Output:**
Progressive rendering via SSE (v2 protocol):
1. Skeleton loader appears immediately.
2. `hukum_item` events render legal basis cards one-by-one (top section).
3. `analisis_delta` tokens stream into the analysis section (middle).
4. `perlu_item` / `action_item` events append to their sections.
5. On `done`, full response is committed to local state.

**Constraints:**
- Must use `/api/chat/stream-v2` endpoint exclusively (v1 is deprecated).
- Citation markers `[n]` in analisis text must be clickable and resolve to the nth hukum item.
- If stream errors mid-flight, show partial content with a "Retry" button that re-sends the same message.
- File attachments are base64-encoded client-side before sending.

**Edge Cases:**
- Network disconnect during stream: show last received content + reconnect prompt.
- Empty hukum array: skip legal basis section, show only analisis.
- Backend returns `perlu_dikonfirmasi` with `type: "file"`: render a file-upload input inline.
- Token expires mid-stream: catch 401, redirect to login, preserve draft message in localStorage.

**Acceptance Criteria:**
- First `hukum_item` renders within 2s of submit on typical queries.
- User can scroll analisis text while it's still streaming.
- Clicking `[n]` citation opens the citation detail panel with correct provision.
- File uploads > 10MB show a client-side error before sending.

---

### 3.2 Conversation Management

**Trigger:** User opens the app, creates/switches/searches conversations.

**Input:** User interactions with conversation list in sidebar.

**Output:**
- Left sidebar shows conversation list (most recent first, pinned at top).
- New conversation button creates a fresh session.
- Clicking a conversation loads its messages from local storage.
- Search input filters conversations by title and message content.

**Constraints:**
- All conversation data persists in IndexedDB (no backend storage).
- Maximum 200 conversations stored; oldest auto-pruned beyond limit. [ASSUMED: pruning threshold]
- Conversation title auto-generates from the first user message (first 60 chars).

**Edge Cases:**
- IndexedDB unavailable (private browsing): fall back to in-memory, warn user data won't persist.
- Conversation deleted while it's the active view: redirect to new conversation.

**Acceptance Criteria:**
- Switching conversations takes < 100ms for conversations with < 50 messages.
- Search returns results within 200ms for the full conversation corpus.
- Pin/unpin is immediate (optimistic UI).

---

### 3.3 Citation Panel

**Trigger:** User clicks a `[n]` marker in analisis text, or clicks a hukum card, or opens the citation sidebar.

**Input:** `node_id` from the citation's `legal_basis` field.

**Output:**
- Right panel slides open showing provision detail.
- Fetches from `/api/provision/{node_id}` on first access, caches locally.
- Shows: regulation title, provision number, full text, child provisions, related norms.
- "Bookmark" button saves citation to UserPreferences.

**Constraints:**
- Panel width: 400px on desktop, full-screen overlay on mobile.
- Provision text is rendered as-is (no markdown interpretation — it's raw legal text).
- Cache provisions in memory for the session; persist bookmarked ones in IndexedDB.

**Edge Cases:**
- `node_id` not found in graph (404): show "Provision not found" with the raw legal_basis string.
- Extremely long provision text (> 5000 chars): virtualized scroll.
- User clicks citation while panel is already showing a different provision: replace content with transition.

**Acceptance Criteria:**
- Cached provisions load instantly (< 50ms).
- First-time provision fetch completes in < 500ms on corporate network.
- Bookmark state persists across sessions.

---

### 3.4 Document Compliance Analysis

**Trigger:** User uploads a document (PDF) for compliance checking.

**Input:**
- File attachment via drag-drop or file picker.
- Sent as part of a chat message (the message can be empty — the file is the intent).

**Output:**
- Compliance scorecard rendered as a dedicated response layout:
  - Score badge (0-100, color-coded: green > 80, yellow 60-80, red < 60).
  - Doc type label.
  - Summary paragraph.
  - Violations list with severity badges and legal basis links.
  - Compliant items (collapsible, default collapsed).
  - Action items with priority ordering.

**Constraints:**
- Uses `/api/chat/upload` endpoint (non-streaming, multipart).
- Only PDF files supported. [OPEN: Should DOCX be supported?]
- Max file size: 10MB client-side validation.

**Edge Cases:**
- Non-PDF file uploaded: client-side rejection with clear error message.
- PDF with no extractable text (scanned image): backend returns low-confidence result — frontend shows warning banner.
- Compliance score is null (backend couldn't classify doc type): show "Unrecognized document" state.

**Acceptance Criteria:**
- Upload progress indicator shows during base64 encoding.
- Scorecard renders progressively (violations first, compliant items last).
- Each violation's legal_basis is clickable and opens citation panel.

---

### 3.5 Severance Calculator

**Trigger:** User navigates to calculator page or clicks a "Calculate" quick action from chat.

**Input:**
- `years_of_service: number` (required, 0-50)
- `monthly_salary: number` (required, > 0)
- `termination_reason: enum` — from backend-defined list
- Additional parameters depending on reason

**Output:**
- Breakdown table: pesangon, penghargaan masa kerja, uang penggantian hak.
- Total amount (formatted as IDR currency).
- Legal basis citations for each component.
- "Share to chat" button that creates a conversation with the result context.

**Constraints:**
- Uses `/api/calculate/severance` endpoint (non-streaming, synchronous).
- Results are cached in `recent_calculations` (last 10).

**Edge Cases:**
- Invalid combination: show inline validation, disable submit.
- Backend returns error for edge-case inputs: show error message with suggestion to consult chat.
- Very large salary values: format with IDR thousand separators correctly.

**Acceptance Criteria:**
- Calculation returns in < 1s.
- Re-opening calculator pre-fills last-used inputs.
- Currency formatting follows Indonesian convention (Rp 1.000.000).

---

### 3.6 Quick Actions and Follow-Up Questions

**Trigger:** Assistant response includes `quick_actions[]` or `perlu_dikonfirmasi[]`.

**Input:** User clicks a quick action chip or answers a follow-up question.

**Output:**
- Quick actions: clicking sends the text as a new user message in the same conversation.
- Follow-up questions: render appropriate input controls based on `type`:
  - `select` → dropdown/radio with provided `options`
  - `number` → numeric input
  - `text` → text input
  - `file` → file picker
- Submitting answers sends a formatted response message.

**Constraints:**
- Quick actions appear below the response, disappear after one is clicked or next message is sent.
- Follow-up questions persist until answered or conversation moves on.
- Maximum 5 quick actions displayed.

**Edge Cases:**
- Follow-up question with `type: "file"` should reuse the same upload mechanism.
- User ignores follow-up questions and types a new message: fine — questions remain but don't block.

**Acceptance Criteria:**
- Clicking quick action immediately shows as user message and triggers stream.
- Follow-up question answers are formatted so backend can extract parameter values.

---

### 3.7 Authentication

**Trigger:** App load, token expiration, explicit logout.

**Input:** Username + password on login form.

**Output:**
- Successful login: token stored in localStorage, redirect to chat.
- Failed login: error message (generic "Invalid credentials").
- Token expiry: redirect to login with return URL preserved.

**Constraints:**
- Token validated on app load via `/api/auth/check`.
- All API calls include `Authorization: Bearer {token}` header.
- 401 from any endpoint triggers logout + redirect.

**Edge Cases:**
- Multiple tabs: token invalidation in one tab should propagate (storage event listener).
- Rate limiting (5 attempts/5 min): show countdown timer after limit hit.

**Acceptance Criteria:**
- Login-to-chat transition < 500ms.
- Token expiry during active use shows a non-destructive prompt.

---

### 3.8 Settings

**Trigger:** User navigates to settings page.

**Input:** Model selection, base URL configuration.

**Output:**
- Current model + available models list from `/api/settings/models`.
- Save updates via `POST /api/settings`.

**Constraints:**
- Changes take effect on next chat message.

**Edge Cases:**
- Selected model no longer available: show warning.
- Invalid base_url: validate with a test call before saving.

**Acceptance Criteria:**
- Model switch confirmed with success toast.
- Settings page loads available models within 2s.

---

### 3.9 Responsive Layout

**Trigger:** Viewport resize, mobile access.

**Output:**
- `>= 1024px` (desktop): Three-column — conversation sidebar | chat | citation panel (collapsible).
- `768-1023px` (tablet): Two-column — sidebar collapses to hamburger | chat | citation panel as overlay.
- `< 768px` (mobile): Single column — bottom nav, full-screen views, citation as full-page push.

**Constraints:**
- Touch targets minimum 44px on mobile.
- Chat input pinned to bottom on all viewports.
- No horizontal scroll on any breakpoint.

**Acceptance Criteria:**
- All core read flows usable at 375px width.
- No layout shift when citation panel opens/closes on desktop.

---

## 4. First-Principles Analysis

### Load-bearing decisions

1. **IndexedDB as persistence layer.** No backend storage for conversations means all history is device-local. Acceptable for 5-10 users on dedicated workstations.

2. **V2 streaming exclusively.** Committing to v2 only simplifies the frontend.

3. **Citation resolution is synchronous on-click.** Provision detail fetched on demand rather than pre-fetched. Mitigation: prefetch provisions for visible hukum cards after stream completes.

4. **Calculator as standalone page (not chat sub-flow).** Both paths work — standalone for known inputs, chat for exploratory questions.

5. **No backend changes for conversation persistence.** No cross-device sync, no conversation sharing. Acceptable for small team.

---

## 5. Resolution Surface

### OPEN

| Item | Default if unresolved |
|------|----------------------|
| DOCX support in compliance pipeline | Accept PDF only in v1 |
| Conversation export/sharing | Not in v1 — "Copy as text" for individual responses |
| Offline capability | No offline for v1 |

### ASSUMED

| Assumption | Risk if wrong |
|------------|---------------|
| Single-device usage per user | Add sync later |
| All users have equal permissions | Add role claim to token |
| 200 conversation storage limit | Increase or add pagination |
| Indonesian-only UI | Minimal i18n cost later |
| Calculator independent of chat | "Share to chat" bridge covers integration |
| localStorage auth caching | Background check handles expiry gracefully |
