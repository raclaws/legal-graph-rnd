import type { ChatResponse, SeveranceRequest, SeveranceResponse, ProvisionResponse, ExplainResponse } from '../types'

const BASE = ''

export interface ComplianceCheckRequest {
  context: Record<string, unknown>
}

export interface ComplianceCheckResult {
  norm_id: string
  norm_description: string
  status: 'pass' | 'violation' | 'warning' | 'unknown'
  severity: string
  detail: string
  legal_basis: string
}

export interface ComplianceCheckResponse {
  summary: { passed: number; warnings: number; violations: number }
  results: ComplianceCheckResult[]
}

export async function sendMessage(
  message: string,
  sessionId?: string,
  context?: Record<string, unknown>,
): Promise<ChatResponse> {
  const res = await fetch(`${BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, message, context }),
  })
  if (!res.ok) throw new Error(`Chat failed: ${res.status}`)
  return res.json()
}

export interface StreamCallbacks {
  onStatus?: (text: string) => void
  onToken?: (text: string) => void
  onComplete?: (data: Record<string, unknown>, sessionId: string) => void
  onError?: (err: Error) => void
}

export async function sendMessageStream(
  message: string,
  callbacks: StreamCallbacks,
  sessionId?: string,
): Promise<void> {
  const res = await fetch(`${BASE}/api/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, message }),
  })

  if (!res.ok) {
    callbacks.onError?.(new Error(`Stream failed: ${res.status}`))
    return
  }

  const reader = res.body?.getReader()
  if (!reader) return

  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      const payload = line.slice(6)
      if (payload === '[DONE]') return

      try {
        const event = JSON.parse(payload)
        if (event.type === 'status') callbacks.onStatus?.(event.text)
        else if (event.type === 'token' || event.type === 'text') callbacks.onToken?.(event.delta || event.text)
        else if (event.type === 'complete') callbacks.onComplete?.(event.data, event.session_id)
      } catch { /* skip malformed */ }
    }
  }
}

export async function sendMessageWithFile(
  message: string,
  file: File,
  sessionId?: string,
): Promise<ChatResponse> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('message', message)
  if (sessionId) formData.append('session_id', sessionId)

  const res = await fetch(`${BASE}/api/chat/upload`, {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`)
  return res.json()
}

export async function checkCompliance(req: ComplianceCheckRequest): Promise<ComplianceCheckResponse> {
  const res = await fetch(`${BASE}/api/compliance/check`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })
  if (!res.ok) throw new Error(`Compliance check failed: ${res.status}`)
  return res.json()
}

export async function calculateSeverance(req: SeveranceRequest): Promise<SeveranceResponse> {
  const res = await fetch(`${BASE}/api/calculate/severance`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })
  if (!res.ok) throw new Error(`Calculator failed: ${res.status}`)
  return res.json()
}

export async function getProvision(nodeId: string): Promise<ProvisionResponse> {
  const res = await fetch(`${BASE}/api/provision/${nodeId}`)
  if (!res.ok) throw new Error(`Provision not found: ${res.status}`)
  return res.json()
}

export async function explainTerm(term: string): Promise<ExplainResponse> {
  const res = await fetch(`${BASE}/api/explain?term=${encodeURIComponent(term)}`)
  if (!res.ok) throw new Error(`Explain failed: ${res.status}`)
  return res.json()
}
