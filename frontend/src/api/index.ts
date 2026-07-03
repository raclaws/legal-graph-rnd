import type { ChatResponse, SeveranceRequest, SeveranceResponse, ProvisionResponse } from '../types'

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
