import { useState, useRef, useEffect, useMemo } from 'react'
import type { PerluDikonfirmasiItem } from '../types'
import { sendMessageWithFile } from '../api'
import Markdown from '../components/shared/Markdown'
import ChatMessage from '../components/chat/ChatMessage'
import ChatInput from '../components/chat/ChatInput'
import ProvisionPanel from '../components/shared/ProvisionPanel'

interface HukumCard {
  description: string
  legal_basis: string
  severity: string
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  hukum?: HukumCard[]
  analisis?: string
  perlu?: PerluDikonfirmasiItem[]
}

function formatPasal(nodeId: string): string {
  const m = nodeId.match(/^(\w+)\/(\d+)\/(\d+)\/.*?Pasal\/(\d+\w*)/)
  if (m) return `${m[1]} ${m[3]}/${m[2]} Ps. ${m[4]}`
  return nodeId
}

function severityBadge(s: string) {
  switch (s) {
    case 'critical': return 'bg-red-100 text-red-800'
    case 'high': return 'bg-orange-100 text-orange-800'
    case 'medium': return 'bg-yellow-100 text-yellow-800'
    default: return 'bg-blue-100 text-blue-700'
  }
}

function AnalisisWithCitations({ text, hukumCards, loading, onCitationClick }: {
  text: string
  hukumCards: HukumCard[]
  loading: boolean
  onCitationClick: (nodeId: string, idx: number) => void
}) {
  const segments = text.split(/\[(\d+)\]/)

  return (
    <div className="text-sm text-gray-700 whitespace-pre-line">
      {segments.map((seg, i) => {
        if (i % 2 === 1) {
          const idx = parseInt(seg, 10) - 1
          const card = hukumCards[idx]
          return (
            <sup
              key={i}
              onClick={() => card?.legal_basis && onCitationClick(card.legal_basis, idx)}
              className={`font-semibold text-[9px] ml-0.5 ${card?.legal_basis ? 'text-blue-600 cursor-pointer hover:text-blue-800' : 'text-gray-400'}`}
              title={card ? formatPasal(card.legal_basis) : ''}
            >
              {seg}
            </sup>
          )
        }
        return <span key={i}><Markdown text={seg} /></span>
      })}
      {loading && <span className="inline-block w-0.5 h-4 bg-amber-600 animate-pulse ml-0.5 align-text-bottom" />}
    </div>
  )
}

function PerluSection({ items, onSubmit }: { items: PerluDikonfirmasiItem[]; onSubmit: (answers: string) => void }) {
  const [values, setValues] = useState<Record<string, string>>({})
  const [submitted, setSubmitted] = useState(false)

  function setValue(key: string, val: string) {
    setValues(prev => ({ ...prev, [key]: val }))
  }

  function handleSubmit() {
    const parts = items
      .map(q => {
        const key = q.parameter_key || q.question
        const val = values[key]
        if (!val) return null
        return `${q.question} → ${val}`
      })
      .filter(Boolean)

    if (parts.length === 0) return
    onSubmit(parts.join('\n'))
    setSubmitted(true)
  }

  if (submitted) {
    return (
      <div className="border-l-4 border-green-400 bg-green-50 rounded-r-lg p-3">
        <p className="text-xs text-green-700">Jawaban terkirim, menunggu analisis...</p>
      </div>
    )
  }

  const filledCount = items.filter(q => values[q.parameter_key || q.question]?.trim()).length

  return (
    <div className="border-l-4 border-violet-400 bg-violet-50 rounded-r-lg p-4">
      <h4 className="text-xs font-semibold text-violet-700 uppercase tracking-wide mb-3">Perlu Dikonfirmasi</h4>
      <div className="space-y-3">
        {items.map((q, i) => {
          const key = q.parameter_key || q.question
          return (
            <div key={i} className="bg-white rounded border border-violet-100 p-3">
              <p className="text-sm font-medium text-gray-700">{q.question}</p>
              {q.why && <p className="text-xs text-gray-500 mt-0.5 mb-2">{q.why}</p>}

              {q.type === 'select' && q.options ? (
                <div className="flex flex-wrap gap-1.5 mt-1">
                  {q.options.map((opt, j) => (
                    <button
                      key={j}
                      onClick={() => setValue(key, opt)}
                      className={`rounded-full border px-3 py-1 text-xs transition-colors ${values[key] === opt ? 'border-violet-500 bg-violet-100 text-violet-700 font-medium' : 'border-gray-200 text-gray-600 hover:bg-gray-100'}`}
                    >
                      {opt}
                    </button>
                  ))}
                </div>
              ) : q.type === 'number' ? (
                <input
                  type="number"
                  value={values[key] || ''}
                  onChange={e => setValue(key, e.target.value)}
                  placeholder="0"
                  className="mt-1 rounded border border-gray-300 px-2 py-1.5 text-sm w-full focus:outline-none focus:ring-1 focus:ring-violet-400"
                />
              ) : (
                <input
                  type="text"
                  value={values[key] || ''}
                  onChange={e => setValue(key, e.target.value)}
                  placeholder="Ketik jawaban..."
                  className="mt-1 rounded border border-gray-300 px-2 py-1.5 text-sm w-full focus:outline-none focus:ring-1 focus:ring-violet-400"
                />
              )}
            </div>
          )
        })}
      </div>

      <div className="flex gap-2 mt-3">
        <button
          onClick={handleSubmit}
          disabled={filledCount === 0}
          className="rounded bg-violet-600 px-4 py-1.5 text-xs font-medium text-white hover:bg-violet-700 disabled:opacity-30"
        >
          Kirim ({filledCount}/{items.length})
        </button>
        <button
          onClick={() => setValues({})}
          className="rounded border border-gray-300 px-4 py-1.5 text-xs text-gray-600 hover:bg-gray-100"
        >
          Batal
        </button>
      </div>
    </div>
  )
}

function HukumSidebarLab({ cards, focusedIndex, onCitationClick }: {
  cards: HukumCard[]
  focusedIndex: number | null
  onCitationClick: (nodeId: string) => void
}) {
  const refs = useRef<(HTMLLIElement | null)[]>([])

  useEffect(() => {
    if (focusedIndex !== null && refs.current[focusedIndex]) {
      refs.current[focusedIndex]?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }, [focusedIndex])

  if (cards.length === 0) return null

  return (
    <aside className="fixed top-[57px] right-0 w-80 h-[calc(100vh-57px)] border-l border-gray-200 bg-white overflow-y-auto z-40">
      <div className="px-4 py-3 border-b border-gray-100 sticky top-0 bg-white">
        <h3 className="text-xs font-semibold text-blue-700 uppercase tracking-wide">Dasar Hukum</h3>
        <p className="text-[10px] text-gray-400 mt-0.5">{cards.length} ketentuan</p>
      </div>
      <ul className="divide-y divide-gray-100">
        {cards.map((card, i) => (
          <li
            key={i}
            ref={el => { refs.current[i] = el }}
            onClick={() => card.legal_basis && onCitationClick(card.legal_basis)}
            className={`px-4 py-3 transition-colors animate-[fadeSlideIn_0.2s_ease-out] ${card.legal_basis ? 'cursor-pointer' : ''} ${focusedIndex === i ? 'bg-blue-50 ring-1 ring-blue-200' : 'hover:bg-gray-50'}`}
          >
            <div className="flex items-start gap-2">
              <span className={`shrink-0 mt-0.5 rounded px-1.5 py-0.5 text-[10px] font-medium ${severityBadge(card.severity)}`}>
                {card.legal_basis ? formatPasal(card.legal_basis) : card.severity}
              </span>
              <p className="text-xs text-gray-700 leading-relaxed">{card.description}</p>
            </div>
          </li>
        ))}
      </ul>
    </aside>
  )
}

export default function ChatLab() {
  const [messages, setMessages] = useState<Message[]>([])
  const [sessionId, setSessionId] = useState<string>()
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState('')
  const [streamingHukum, setStreamingHukum] = useState<HukumCard[]>([])
  const [streamingAnalisis, setStreamingAnalisis] = useState('')
  const [streamingPerlu, setStreamingPerlu] = useState<PerluDikonfirmasiItem[]>([])
  const [focusedHukum, setFocusedHukum] = useState<number | null>(null)
  const [panelNodeId, setPanelNodeId] = useState<string | null>(null)
  const endRef = useRef<HTMLDivElement>(null)

  const allHukum = useMemo(() => {
    const items: HukumCard[] = []
    const seen = new Set<string>()
    for (const msg of messages) {
      for (const h of (msg.hukum || [])) {
        const key = `${h.legal_basis}||${h.description}`
        if (!seen.has(key)) { seen.add(key); items.push(h) }
      }
    }
    for (const h of streamingHukum) {
      const key = `${h.legal_basis}||${h.description}`
      if (!seen.has(key)) { seen.add(key); items.push(h) }
    }
    return items
  }, [messages, streamingHukum])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingAnalisis, streamingPerlu])

  function handleCitationClick(nodeId: string, idx?: number) {
    setPanelNodeId(nodeId)
    if (idx !== undefined) {
      setFocusedHukum(idx)
      setTimeout(() => setFocusedHukum(null), 2000)
    }
  }

  async function handleSend(text: string, file?: File) {
    const message = text || input
    if (!message.trim() || loading) return
    setInput('')
    setLoading(true)
    setStatus('')
    setStreamingHukum([])
    setStreamingAnalisis('')
    setStreamingPerlu([])

    const userContent = file ? `${message}\n\n📎 ${file.name}` : message
    setMessages(prev => [...prev, { role: 'user', content: userContent }])

    // File upload uses the non-streaming endpoint
    if (file) {
      try {
        const res = await sendMessageWithFile(message, file, sessionId)
        setSessionId(res.session_id)
        const response = res.response
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: '',
          hukum: response.hukum,
          analisis: response.analisis?.text || '',
          perlu: response.perlu_dikonfirmasi,
        }])
      } catch {
        setMessages(prev => [...prev, { role: 'assistant', content: 'Gagal upload. Coba lagi.' }])
      } finally {
        setLoading(false)
      }
      return
    }

    try {
      const token = localStorage.getItem('auth_token')
      const res = await fetch('/api/chat/stream-v2', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ message, session_id: sessionId }),
      })

      if (!res.ok) {
        setMessages(prev => [...prev, { role: 'assistant', content: 'Gagal memproses. Coba lagi.' }])
        setLoading(false)
        return
      }

      const reader = res.body?.getReader()
      if (!reader) return

      const decoder = new TextDecoder()
      let buffer = ''
      const collectedHukum: HukumCard[] = []
      let collectedAnalisis = ''
      const collectedPerlu: PerluDikonfirmasiItem[] = []

      while (true) {
        const { done: streamDone, value } = await reader.read()
        if (streamDone) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const payload = line.slice(6)
          if (payload === '[DONE]') break

          try {
            const event = JSON.parse(payload)

            switch (event.type) {
              case 'status':
                setStatus(event.data?.text || '')
                break
              case 'hukum_item':
                collectedHukum.push(event.data)
                setStreamingHukum([...collectedHukum])
                setStatus('')
                break
              case 'analisis_delta':
                collectedAnalisis += event.delta
                setStreamingAnalisis(collectedAnalisis)
                setStatus('')
                break
              case 'perlu_item':
                collectedPerlu.push(event.data)
                setStreamingPerlu([...collectedPerlu])
                break
              case 'done':
                if (event.data?.session_id) setSessionId(event.data.session_id)
                setMessages(prev => [...prev, {
                  role: 'assistant',
                  content: '',
                  hukum: collectedHukum,
                  analisis: collectedAnalisis,
                  perlu: collectedPerlu,
                }])
                setStreamingHukum([])
                setStreamingAnalisis('')
                setStreamingPerlu([])
                break
              case 'error':
                setMessages(prev => [...prev, { role: 'assistant', content: event.data?.text || 'Error' }])
                break
            }
          } catch { /* skip malformed */ }
        }
      }
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Tidak dapat terhubung ke server.' }])
    } finally {
      setLoading(false)
      setStatus('')
    }
  }

  const hasSidebar = allHukum.length > 0

  return (
    <div className="flex flex-col h-[calc(100vh-57px)]">
      <div className="flex-1 overflow-y-auto px-4 py-6" style={{ paddingRight: hasSidebar && !panelNodeId ? '21rem' : panelNodeId ? '25rem' : undefined }}>
        <div className="max-w-3xl mx-auto space-y-4">
          {messages.length === 0 && !loading && (
            <div className="mt-20 text-center">
              <h1 className="text-2xl font-semibold text-gray-900 mb-2">Streaming Lab</h1>
              <p className="text-sm text-gray-500 mb-6">Progressive rendering — each section appears as it arrives</p>
              <div className="flex flex-wrap justify-center gap-2">
                {['Hak cuti tahunan', 'PKWT max berapa tahun?', 'Hitung pesangon 5 tahun'].map(q => (
                  <button
                    key={q}
                    onClick={() => handleSend(q)}
                    className="rounded-full border border-gray-200 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i}>
              {msg.role === 'user' ? (
                <ChatMessage
                  role="user"
                  content={msg.content}
                  onRetry={() => {
                    setMessages(prev => prev.slice(0, i))
                    setTimeout(() => handleSend(msg.content), 0)
                  }}
                />
              ) : msg.analisis ? (
                <div className="space-y-3">
                  <div className="border-l-4 border-amber-400 bg-amber-50 rounded-r-lg p-4">
                    <h4 className="text-[10px] font-semibold text-amber-700 uppercase tracking-wide mb-2">Analisis</h4>
                    <AnalisisWithCitations text={msg.analisis} hukumCards={msg.hukum || []} loading={false} onCitationClick={handleCitationClick} />
                  </div>
                  {msg.perlu && msg.perlu.length > 0 && (
                    <PerluSection items={msg.perlu} onSubmit={handleSend} />
                  )}
                </div>
              ) : (
                <ChatMessage role="assistant" content={msg.content} />
              )}
            </div>
          ))}

          {/* Streaming state */}
          {loading && status && (
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <div className="flex gap-0.5">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
                <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse [animation-delay:0.2s]" />
                <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse [animation-delay:0.4s]" />
              </div>
              {status}
            </div>
          )}

          {loading && streamingAnalisis && (
            <div className="border-l-4 border-amber-400 bg-amber-50 rounded-r-lg p-4">
              <h4 className="text-[10px] font-semibold text-amber-700 uppercase tracking-wide mb-2">Analisis</h4>
              <AnalisisWithCitations text={streamingAnalisis} hukumCards={streamingHukum} loading={true} onCitationClick={handleCitationClick} />
            </div>
          )}

          {loading && streamingPerlu.length > 0 && (
            <PerluSection items={streamingPerlu} onSubmit={handleSend} />
          )}

          <div ref={endRef} />
        </div>
      </div>

      {/* Input — with file attachment */}
      <div className="border-t border-gray-200 bg-white px-4 py-3 pb-safe" style={{ paddingRight: hasSidebar && !panelNodeId ? '21rem' : panelNodeId ? '25rem' : undefined }}>
        <div className="max-w-3xl mx-auto">
          <ChatInput onSend={handleSend} disabled={loading} />
        </div>
      </div>

      {/* Sidebar — hukum cards stream here */}
      <HukumSidebarLab cards={allHukum} focusedIndex={focusedHukum} onCitationClick={handleCitationClick} />

      {/* Provision panel — opens when clicking sidebar card or superscript */}
      <ProvisionPanel nodeId={panelNodeId} onClose={() => setPanelNodeId(null)} />
    </div>
  )
}
