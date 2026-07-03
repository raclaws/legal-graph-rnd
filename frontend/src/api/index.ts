import type { ChatResponse, SeveranceRequest, SeveranceResponse, ProvisionResponse, ExplainResponse } from '../types'

const BASE = ''

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
