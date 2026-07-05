import { useState, useRef, useEffect, useCallback } from 'react'
import type { PerluDikonfirmasiItem } from '../types'
import Markdown from '../components/shared/Markdown'

interface HukumCard {
  description: string
  legal_basis: string
  severity: string
}

function formatPasal(nodeId: string): string {
  const m = nodeId.match(/^(\w+)\/(\d+)\/(\d+)\/.*?Pasal\/(\d+\w*)/)
  if (m) return `${m[1]} ${m[3]}/${m[2]} Ps. ${m[4]}`
  return nodeId
}

function severityColor(s: string) {
  switch (s) {
    case 'critical': return 'border-red-400 bg-red-50'
    case 'high': return 'border-orange-400 bg-orange-50'
    case 'medium': return 'border-yellow-400 bg-yellow-50'
    default: return 'border-blue-400 bg-blue-50'
  }
}

function severityBadge(s: string) {
  switch (s) {
    case 'critical': return 'bg-red-100 text-red-800'
    case 'high': return 'bg-orange-100 text-orange-800'
    case 'medium': return 'bg-yellow-100 text-yellow-800'
    default: return 'bg-blue-100 text-blue-700'
  }
}

export default function ChatLab() {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState('')
  const [hukumCards, setHukumCards] = useState<HukumCard[]>([])
  const [analisisText, setAnalisisText] = useState('')
  const [perluItems, setPerluItems] = useState<PerluDikonfirmasiItem[]>([])
  const [done, setDone] = useState(false)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [hukumCards, analisisText, perluItems])

  const reset = useCallback(() => {
    setHukumCards([])
    setAnalisisText('')
    setPerluItems([])
    setDone(false)
    setStatus('')
  }, [])

  async function handleSend(text?: string) {
    const message = text || input
    if (!message.trim() || loading) return
    setInput('')
    setLoading(true)
    reset()

    try {
      const token = localStorage.getItem('auth_token')
      const res = await fetch('/api/chat/stream-v2', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ message }),
      })

      if (!res.ok) {
        setStatus('Error: ' + res.status)
        setLoading(false)
        return
      }

      const reader = res.body?.getReader()
      if (!reader) return

      const decoder = new TextDecoder()
      let buffer = ''

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
                setStatus(event.data?.text || event.delta || '')
                break
              case 'hukum_item':
                setHukumCards(prev => [...prev, event.data])
                setStatus('')
                break
              case 'analisis_delta':
                setAnalisisText(prev => prev + event.delta)
                setStatus('')
                break
              case 'perlu_item':
                setPerluItems(prev => [...prev, event.data])
                break
              case 'done':
                setDone(true)
                break
              case 'error':
                setStatus('Error: ' + (event.data?.text || 'Unknown'))
                break
            }
          } catch { /* skip malformed */ }
        }
      }
    } catch {
      setStatus('Connection failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-57px)]">
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-3xl mx-auto space-y-3">
          {/* Empty state */}
          {!loading && !done && hukumCards.length === 0 && !analisisText && (
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

          {/* Status indicator */}
          {status && (
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <div className="flex gap-0.5">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
                <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse [animation-delay:0.2s]" />
                <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse [animation-delay:0.4s]" />
              </div>
              {status}
            </div>
          )}

          {/* Hukum cards — appear one by one */}
          {hukumCards.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide">Dasar Hukum</h4>
              {hukumCards.map((card, i) => (
                <div
                  key={i}
                  className={`border-l-4 rounded-r-lg p-3 animate-[fadeSlideIn_0.2s_ease-out] ${severityColor(card.severity)}`}
                >
                  <div className="flex items-start gap-2">
                    <span className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium ${severityBadge(card.severity)}`}>
                      {card.legal_basis ? formatPasal(card.legal_basis) : card.severity}
                    </span>
                    <p className="text-sm text-gray-700">{card.description}</p>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Analisis — streams in real-time */}
          {analisisText && (
            <div className="border-l-4 border-amber-400 bg-amber-50 rounded-r-lg p-4 animate-[fadeSlideIn_0.2s_ease-out]">
              <h4 className="text-[10px] font-semibold text-amber-700 uppercase tracking-wide mb-2">Analisis</h4>
              <div className="text-sm text-gray-700 whitespace-pre-line">
                <Markdown text={analisisText} />
                {loading && <span className="inline-block w-0.5 h-4 bg-amber-600 animate-pulse ml-0.5 align-text-bottom" />}
              </div>
            </div>
          )}

          {/* Perlu dikonfirmasi — slides in at the end */}
          {perluItems.length > 0 && (
            <div className="border-l-4 border-violet-400 bg-violet-50 rounded-r-lg p-4 animate-[fadeSlideIn_0.2s_ease-out]">
              <h4 className="text-[10px] font-semibold text-violet-700 uppercase tracking-wide mb-2">Perlu Dikonfirmasi</h4>
              <div className="space-y-2">
                {perluItems.map((q, i) => (
                  <div key={i} className="bg-white rounded border border-violet-100 p-3">
                    <p className="text-sm font-medium text-gray-700">{q.question}</p>
                    {q.why && <p className="text-xs text-gray-500 mt-0.5">{q.why}</p>}
                    {q.options && (
                      <div className="flex flex-wrap gap-1.5 mt-2">
                        {q.options.map((opt, j) => (
                          <span key={j} className="rounded-full border border-violet-200 px-3 py-1 text-xs text-violet-700">
                            {opt}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Done marker */}
          {done && (
            <p className="text-[10px] text-gray-400 text-center pt-2">Selesai</p>
          )}

          <div ref={endRef} />
        </div>
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 bg-white px-4 py-3 pb-safe">
        <div className="max-w-3xl mx-auto">
          <form
            onSubmit={e => { e.preventDefault(); handleSend() }}
            className="flex gap-2"
          >
            <input
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="Ketik pertanyaan..."
              disabled={loading}
              className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-40"
            >
              Kirim
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
