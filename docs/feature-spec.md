# HR Compliance Frontend Redesign — Feature Spec + Design Direction

---

# PART A — FEATURE SPEC

## 1. Feature Summary

| # | PRD Feature | Summary |
|---|-------------|---------|
| 3.1 | Streaming Chat | Progressive SSE rendering via `/api/chat/stream-v2` — hukum cards, analisis text, follow-ups |
| 3.2 | Conversation Management | IndexedDB-persisted threads with search, pin, archive |
| 3.3 | Citation Panel | Right-side provision detail panel with bookmark capability |
| 3.4 | Document Compliance Analysis | PDF upload → scorecard with violations/compliant/actions |
| 3.5 | Severance Calculator | Standalone input form → breakdown table with legal basis |
| 3.6 | Quick Actions & Follow-Up Questions | Chips and interactive inputs rendered from structured response |
| 3.7 | Authentication | Login form, token persistence, 401 interception, rate limit display |
| 3.8 | Settings | Model selection, base URL configuration |
| 3.9 | Responsive Layout | 3-column → 2-column overlay → single column + bottom nav |

---

## 2. Screen Inventory

| Screen | Route | Layout Columns | Purpose |
|--------|-------|----------------|---------|
| Login | `/login` | Full-bleed single | Auth gate |
| Chat | `/` | 3 (sidebar / main / citation) | Primary workspace |
| Calculator | `/calculator` | 2 (form / results) | Severance computation |
| Settings | `/settings` | Single centered | Model + URL config |
| Empty State | `/` (no conversations) | Single centered | Onboarding prompt |

**Overlays (not routes):**
- Citation Panel (right slide)
- Conversation Search (command palette)
- Document Upload Modal
- Compliance Scorecard Modal

---

## 3. User Flows

### Flow 3.1: Streaming Chat

```
User types message → ChatInput validates non-empty
  → Message entity created (status: sending)
  → POST /api/chat/stream-v2 with { message, session_id?, attachments? }
  → SSE connection opens
  → status events → show skeleton loader text
  → hukum_item events → cards render progressively in citation rail
  → analisis_delta events → text streams into main content area
  → perlu_item events → interactive form fields appear below analisis
  → action_item events → action chips accumulate
  → done event → Message status transitions to complete
  → [DONE] terminal → connection closed
```

**Error path:** `error` event or network failure → Message status: error → retry button appears.

### Flow 3.2: Conversation Management

```
App loads → IndexedDB queried for all Conversations
  → Sidebar populates (sorted: pinned first, then updated_at desc)

New conversation: User clicks "+" or sends first message
  → Conversation entity created { id: uuid, title: first message truncated, created_at }
  → Becomes active conversation

Pin: Long-press or context menu → pinned: true → moves to top section
Archive: Swipe or context menu → state: archived → removed from list

Search: Cmd+K → command palette → filters conversations by title substring
```

### Flow 3.3: Citation Panel

```
User clicks citation superscript [n] in analisis text
  → Extract node_id from corresponding HukumCard.legal_basis
  → Panel slides open from right (or overlays on mobile)
  → GET /api/provision/{node_id}
  → Render: type, number, full text, children list, norms_derived
  → Bookmark icon in panel header → saves to UserPreferences.bookmarked_citations

Navigation within panel:
  → Click child provision → fetches that node_id → panel content replaces
  → Breadcrumb trail builds for back-navigation
```

### Flow 3.4: Document Compliance Analysis

```
User clicks upload button (or drags file onto chat)
  → File picker opens (accept: .pdf, .txt)
  → Document entity created (status: pending)
  → POST /api/chat/upload (multipart: file + message)
  → Response with response_type: "compliance_report"
  → Scorecard renders: score badge, violations[], compliant[], actions[]
  → Document status transitions to analyzed
```

### Flow 3.5: Severance Calculator

```
Navigate to /calculator
  → Form renders: masa_kerja, upah_pokok, tunjangan_tetap, alasan_phk, tanggal_phk
  → User fills fields (alasan_phk is select from enum)
  → POST /api/calculate/severance
  → CalculatorSession created (status: calculated)
  → Results table: pesangon, penghargaan, penggantian_hak, total
  → Each row shows formula + legal_basis
  → Optional: comparison with old law if returned
```

### Flow 3.6: Quick Actions & Follow-Up Questions

```
Stream completes with quick_actions[] in response
  → Chips render below the message
  → Click chip → prefill text inserted into ChatInput → auto-send

perlu_dikonfirmasi[] items render as interactive form:
  → type: "select" → dropdown with options[]
  → type: "number" → number input
  → type: "text" → text field
  → type: "file" → file picker
  → Submit button → formats answers → sends as new message
```

### Flow 3.7: Authentication

```
App loads → check localStorage for token
  → If token exists: GET /api/auth/check
    → 200: proceed to app
    → 401: clear token, redirect to /login
  → If no token: redirect to /login

Login form submit → POST /api/auth/login { username, password }
  → 200: store token in localStorage, redirect to /
  → 401: show "Kredensial tidak valid"
  → 429: show "Terlalu banyak percobaan. Coba lagi nanti." with countdown
```

### Flow 3.8: Settings

```
Navigate to /settings
  → GET /api/settings → populate current model, base_url
  → GET /api/settings/models → populate model dropdown options
  → User changes model or base_url
  → POST /api/settings { model, base_url }
  → Success toast
```

### Flow 3.9: Responsive Layout

```
>=1024px: sidebar (280px) | chat (flex) | citation panel (360px, conditional)
768-1023px: sidebar hidden (hamburger toggle) | chat (full) | citation as overlay
<768px: single column | bottom nav (Chat, Calculator, Settings) | panels as full-screen sheets
```

---

## 4. State Catalog

| Entity | States | Transitions |
|--------|--------|-------------|
| Conversation | active, archived | active → archived (user action) |
| Message | sending, streaming, complete, error | sending → streaming → complete; sending → error; error → sending (retry) |
| Citation | referenced, expanded, bookmarked | referenced → expanded (click); expanded → bookmarked (user action) |
| Document | pending, analyzed, error | pending → analyzed; pending → error |
| CalculatorSession | draft, calculated | draft → calculated (API success) |

**UI-only transient states:**

| Context | States |
|---------|--------|
| Citation panel | closed, loading, loaded, error |
| Conversation sidebar | collapsed, expanded |
| Command palette | closed, open |
| Upload modal | closed, selecting, uploading, complete |

---

## 5. Component Decomposition

### Shell Layer
```
AppShell
├── ConversationSidebar
│   ├── SidebarHeader            # Logo + new conversation button
│   ├── PinnedSection
│   ├── ConversationList
│   │   └── ConversationItem
│   └── SidebarFooter            # Settings + calculator nav
├── MainContent
│   ├── ChatView
│   │   ├── MessageList
│   │   │   ├── UserMessage
│   │   │   └── AssistantMessage
│   │   │       ├── StatusIndicator
│   │   │       ├── HukumCardRail
│   │   │       │   └── HukumCard
│   │   │       ├── AnalisisBlock
│   │   │       ├── ComplianceScorecard
│   │   │       ├── PerluForm
│   │   │       │   └── PerluField
│   │   │       ├── ActionList
│   │   │       │   └── ActionItem
│   │   │       └── QuickActions
│   │   │           └── QuickChip
│   │   └── ChatInput
│   │       ├── AttachmentPreview
│   │       └── SendButton
│   ├── CalculatorView
│   │   ├── CalculatorForm
│   │   └── CalculatorResults
│   │       └── BreakdownRow
│   └── SettingsView
│       ├── ModelSelector
│       └── BaseUrlInput
├── CitationPanel
│   ├── PanelHeader              # Breadcrumb + close + bookmark
│   ├── ProvisionContent
│   ├── ChildrenList
│   └── NormsList
└── CommandPalette
```

### Shared Components
```
Shared/
├── Button                # Primary, secondary, ghost, danger
├── Input                 # Text, number, select, file
├── Badge                 # Severity indicators
├── Skeleton              # Loading placeholders
├── Toast                 # Transient notifications
├── Modal                 # Overlay container
├── Sheet                 # Mobile bottom sheet
├── ScrollArea            # Custom scrollbar
└── Kbd                   # Keyboard shortcut hint
```

---

## 6. Data Requirements

### API Request/Response Shapes (Frontend Contract)

**Chat Stream (primary interaction):**
```typescript
// Request
interface ChatStreamRequest {
  session_id?: string
  message: string
  attachments?: { filename: string; content_type: string; data_base64: string }[]
  context?: Record<string, unknown>
}

// SSE Events consumed:
type SSEEvent =
  | { type: 'status'; data: { text: string } }
  | { type: 'hukum_item'; data: HukumItem }
  | { type: 'analisis_delta'; delta: string }
  | { type: 'perlu_item'; data: PerluDikonfirmasiItem }
  | { type: 'action_item'; data: ActionItem }
  | { type: 'done'; data: { session_id: string } }
  | { type: 'error'; data: { text: string } }
```

**Provision Lookup:**
```typescript
// GET /api/provision/{node_id}
interface ProvisionResponse {
  node_id: string
  type: string
  number: string
  text?: string
  parent?: string
  children: { node_id: string; type: string; number: string; text_preview?: string }[]
  regulation?: Record<string, unknown>
  norms_derived: { id: string; description: string; severity: string }[]
}
```

**Calculator:**
```typescript
interface SeveranceRequest {
  masa_kerja_bulan: number
  upah_pokok: number
  tunjangan_tetap: number
  alasan_phk: string
  tanggal_phk?: string
}

interface SeveranceResponse {
  pesangon: { amount: number; formula: string; multiplier?: number }
  penghargaan: { amount: number; formula: string }
  penggantian_hak: { amount: number; formula: string }
  total: number
  legal_basis: { pasal: string; description: string }[]
  comparison?: { old_law_total: number; difference: number; note: string }
}
```

**Auth:**
```typescript
interface LoginRequest { username: string; password: string }
interface LoginResponse { token: string }
// GET /api/auth/check → { ok: true } or 401
```

**Settings:**
```typescript
interface SettingsResponse { model: string; base_url: string }
interface ModelsResponse { models: string[] }
```

### Caching Strategy

| Data | Store | TTL | Invalidation |
|------|-------|-----|-------------|
| Conversations | IndexedDB | Permanent | User delete/archive |
| Messages | IndexedDB (per conversation) | Permanent | — |
| Auth token | localStorage | 7 days (server-side) | 401 response |
| UserPreferences | localStorage | Permanent | User action |
| Provision data | In-memory LRU (50 entries) | Session | — |
| Calculator results | IndexedDB | Permanent | — |
| Model list | In-memory | 5 minutes | Settings page mount |

---

## 7. Edge Cases and Constraints

### Network
- SSE connection drops mid-stream: show partial content + "Koneksi terputus" banner + retry button
- Slow first byte (>5s): transition from skeleton to "Model sedang memproses..." with elapsed timer
- 429 on login: disable submit, show countdown timer

### Data
- Conversation list exceeds 200: oldest archived auto-purge
- Large analisis text (>10KB): virtualize rendering
- Empty hukum[] array: skip card rail, show analisis directly
- Missing optional fields: graceful null-rendering

### Interaction
- Double-submit: disable send button during streaming
- File too large: validate client-side (10MB limit)
- Rapid citation clicks: abort previous provision fetch
- Mobile keyboard: chat input not obscured

### Auth
- Token expired during active use: queue failed request, non-destructive login prompt
- Concurrent tabs: storage event listener for cross-tab sync

---

## 8. Acceptance Criteria

### Streaming Chat (3.1)
- [ ] Messages stream progressively: hukum cards appear before analisis text begins
- [ ] Citation superscripts clickable and open correct provision
- [ ] Streaming cursor visible during analisis_delta events
- [ ] Error state shows retry button
- [ ] Status text visible during initial status events

### Conversation Management (3.2)
- [ ] Conversations persist across page reloads
- [ ] New conversation starts with "+" or first message
- [ ] Pinned conversations appear above unpinned
- [ ] Cmd+K search filters by title substring <100ms

### Citation Panel (3.3)
- [ ] Panel opens with slide animation
- [ ] Full provision text, children, and norms rendered
- [ ] Clicking child navigates within panel
- [ ] Bookmark persists in localStorage
- [ ] Closeable via X, Escape, or clicking outside

### Document Compliance Analysis (3.4)
- [ ] Accepts .pdf and .txt only
- [ ] Score badge color-coded: green >=80, yellow 50-79, red <50
- [ ] Each violation's legal_basis clickable

### Severance Calculator (3.5)
- [ ] All input fields with Indonesian labels
- [ ] Results table shows formulas
- [ ] Total prominently displayed
- [ ] Currency formatted as Rp 1.000.000

### Quick Actions & Follow-Ups (3.6)
- [ ] Chips render below completed message
- [ ] perlu form renders correct input type per item
- [ ] Submit only enabled when at least one field filled

### Authentication (3.7)
- [ ] Unauthenticated users see only login page
- [ ] 429 displays countdown timer
- [ ] 401 on any API call → redirect to login

### Settings (3.8)
- [ ] Model dropdown populated from /api/settings/models
- [ ] Save shows success toast

### Responsive Layout (3.9)
- [ ] >=1024px: three columns visible
- [ ] <768px: single column with bottom navigation
- [ ] No horizontal scroll at any breakpoint
- [ ] Chat input always accessible

---

# PART B — FRONTEND DESIGN DIRECTION

## 1. Aesthetic Direction

**Core concept: "Legal Intelligence Surface"**

A tool that feels like a private research terminal — dense with information but never overwhelming. The interface communicates authority and precision (this is law) while remaining approachable for non-lawyer HR staff.

**Principles:**
- **Dark-first, light as override.** Dark environments reduce fatigue for daily-use tools and let severity badges pop.
- **Layered depth via translucency, not shadows.** Panels float with backdrop-blur and subtle border-light.
- **Information density with breathing room.** Compact rows with generous line-height.
- **Monochrome canvas, chromatic data.** The shell is neutral. Color is reserved for severity, status, and interactive affordances.
- **Quiet until needed.** Panels, tooltips, and details stay hidden until invoked.

**Reference points:** Linear's density + Raycast's command palette + Notion's sidebar + Arc's spatial layering.

---

## 2. Typography + Color

### Typography

**Font stack:** Inter Variable (primary), JetBrains Mono (code/legal references).

| Role | Family | Size | Weight | Line-height | Letter-spacing |
|------|--------|------|--------|-------------|----------------|
| Page title | Inter | 20px | 600 | 1.3 | -0.02em |
| Section header | Inter | 14px | 600 | 1.4 | -0.01em |
| Body text | Inter | 13px | 400 | 1.6 | 0 |
| Small/caption | Inter | 11px | 400 | 1.4 | 0.01em |
| Legal reference | JetBrains Mono | 11px | 400 | 1.5 | 0 |
| Input text | Inter | 13px | 400 | 1.5 | 0 |
| Badge text | Inter | 10px | 600 | 1.0 | 0.02em |

### Color System

**Dark mode (default):**

| Token | Hex | Usage |
|-------|-----|-------|
| `--bg-base` | #0F0F12 | App background |
| `--bg-surface` | #18181B | Cards, panels |
| `--bg-elevated` | #1F1F23 | Hover states, active items |
| `--bg-overlay` | #18181B/80 | Backdrop-blur panels |
| `--border-subtle` | #27272A | Dividers |
| `--border-default` | #3F3F46 | Input borders |
| `--text-primary` | #FAFAFA | Main content |
| `--text-secondary` | #A1A1AA | Labels, captions |
| `--text-tertiary` | #71717A | Placeholders, disabled |
| `--accent` | #6366F1 | Interactive elements, links |
| `--accent-hover` | #818CF8 | Hover state for accent |

**Semantic colors (severity):**

| Token | Hex | Usage |
|-------|-----|-------|
| `--severity-critical` | #EF4444 | Critical violations |
| `--severity-high` | #F97316 | High severity |
| `--severity-medium` | #EAB308 | Warnings |
| `--severity-low` | #6366F1 | Informational |
| `--success` | #22C55E | Compliant items, score >=80 |
| `--warning` | #EAB308 | Score 50-79 |
| `--error` | #EF4444 | Errors, score <50 |

---

## 3. Component Visual Inventory

### Conversation Sidebar
- Width: 280px (desktop), full-width sheet (mobile)
- Item height: 44px
- Item padding: 12px 16px
- Active item: `--bg-elevated` background + 2px left accent border
- Pin icon: 14px, `--text-tertiary`, positioned right

### Chat Message (User)
- Max-width: 720px, right-aligned
- Padding: 12px 16px
- Background: `--accent` at 10% opacity
- Border-radius: 16px 16px 4px 16px
- Font: 13px/1.6 Inter 400

### Chat Message (Assistant — Structured Response)
- Max-width: 720px, left-aligned
- No background (content speaks)
- Sections separated by 16px gap

### Hukum Card
- Width: 240px (horizontal scroll rail)
- Height: auto, min 80px
- Padding: 12px
- Background: `--bg-surface`
- Border: 1px `--border-subtle`
- Border-radius: 8px
- Severity badge: top-right, 10px text, pill shape
- Gap between cards: 8px

### Citation Panel
- Width: 360px (desktop), full-width sheet (mobile)
- Background: `--bg-surface` with backdrop-blur(12px)
- Header height: 48px
- Content padding: 16px 20px
- Legal text: JetBrains Mono 11px, `--text-secondary`

### Chat Input
- Height: 48px default, expands to max 160px
- Border-radius: 24px
- Background: `--bg-surface`
- Border: 1px `--border-default`, focus: `--accent`
- Padding: 12px 48px 12px 16px
- Send button: 32px circle, `--accent` background

### Compliance Scorecard
- Score badge: 48px circle, centered number (20px bold)
- Violation row: 8px left border (severity color), 12px padding
- Section gap: 12px

### Button
- Height: 32px (sm), 36px (md), 40px (lg)
- Padding: 0 12px (sm), 0 16px (md), 0 20px (lg)
- Border-radius: 6px
- Primary: `--accent` bg, white text
- Secondary: transparent bg, `--border-default` border
- Ghost: transparent bg, no border, `--text-secondary` text

### Badge (Severity)
- Height: 18px
- Padding: 0 6px
- Border-radius: 9px (full pill)
- Font: 10px 600 uppercase
- Background: severity color at 15% opacity
- Text: severity color at full strength

### Quick Action Chip
- Height: 28px
- Padding: 0 12px
- Border-radius: 14px
- Background: `--bg-elevated`
- Border: 1px `--border-subtle`
- Hover: border transitions to `--accent`

---

## 4. Motion Spec

| Interaction | Property | Duration | Easing |
|-------------|----------|----------|--------|
| Panel open | transform: translateX | 200ms | cubic-bezier(0.32, 0.72, 0, 1) |
| Panel close | transform: translateX | 150ms | cubic-bezier(0.32, 0.72, 0, 1) |
| Sidebar toggle | width | 200ms | cubic-bezier(0.32, 0.72, 0, 1) |
| Message appear | opacity + translateY(8px) | 180ms | ease-out |
| Hukum card enter | opacity + translateY(4px) | 150ms | ease-out, stagger 50ms |
| Streaming cursor | opacity | 600ms | step-end (blink) |
| Quick chip hover | border-color | 120ms | ease |
| Score badge | scale(0.8→1) + opacity | 300ms | spring(1, 80, 10) |
| Command palette | opacity + scale(0.96→1) | 150ms | ease-out |
| Toast enter | translateY(-8px) + opacity | 200ms | ease-out |
| Toast exit | opacity | 150ms | ease-in |
| Skeleton pulse | opacity 0.4→1 | 1200ms | ease-in-out infinite |

**Reduced motion:** All transitions collapse to 0ms. Opacity only. Respect `prefers-reduced-motion: reduce`.

---

## 5. What Makes It Memorable

1. **Progressive stream rendering.** Cards slide in one by one, text types character-by-character. It feels alive.

2. **Citation as spatial navigation.** Clicking a superscript opens a provision panel you can drill into. You're navigating a legal graph.

3. **The severity color language.** Four colors are the only chromatic elements in a monochrome interface. Critical violations command attention through contrast.

4. **Command palette as universal entry.** Cmd+K searches conversations, citations, calculations, and legal terms simultaneously.

5. **Dark canvas, bright data.** The interface recedes. Legal content glows.

6. **Density without clutter.** Every pixel communicates data, but generous line-height prevents overwhelm.

---

## 6. Anti-Patterns

| Do NOT | Instead |
|--------|---------|
| Full-page loading spinners | Skeleton placeholders matching final layout |
| Modals for primary flows | Panels and inline expansion |
| Color-coding for navigation | Position, weight, and opacity for hierarchy |
| Toast for errors in chat | Inline error state on the message |
| Transitions >300ms | Keep all motion under 200ms |
| Rounded-everything (>12px) | 6-8px for containers, pill only for badges |
| Gradient backgrounds | Flat surfaces with border-light separation |
| Hamburger menu on desktop | Persistent collapsible sidebar |
| Auto-playing idle animations | Motion only on user-triggered state changes |
| Multiple font families beyond 2 | Inter (UI) + JetBrains Mono (legal) only |
