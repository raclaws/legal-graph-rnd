import { useState, useRef, useEffect, useMemo } from 'react'
import { useChat } from '@ai-sdk/react'
import { DefaultChatTransport } from 'ai'
import type { PerluDikonfirmasiItem, ActionItem } from '../types'
import { sendMessageWithFile, authHeaders } from '../api'
import Markdown from '../components/shared/Markdown'
import ChatMessage from '../components/chat/ChatMessage'
import ChatInput from '../components/chat/ChatInput'
import ProvisionPanel from '../components/shared/ProvisionPanel'

const PIPELINE_STEPS = ['Mencari dasar hukum', 'Menganalisis', 'Menyusun jawaban'] as const

interface HukumCard {
  description: string
  legal_basis: string
  severity: string
  doc_evidence?: string
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  hukum?: HukumCard[]
  analisis?: string
  perlu?: PerluDikonfirmasiItem[]
  actions?: ActionItem[]
  response_type?: 'chat' | 'compliance_report'
  compliance_score?: number
  compliance_doc_type?: string
  compliance_summary?: { compliant: number; violated: number; not_evaluated: number }
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

function ProgressBreadcrumb({ hasHukum, hasAnalisis }: { hasHukum: boolean; hasAnalisis: boolean }) {
  const activeStep = hasAnalisis ? 2 : hasHukum ? 1 : 0
  return (
    <div className="flex items-center gap-1 text-[11px]">
      {PIPELINE_STEPS.map((step, i) => (
        <span key={i} className="flex items-center gap-1">
          {i > 0 && <span className="text-gray-300">→</span>}
          <span className={i === activeStep ? 'text-blue-600 font-medium' : i < activeStep ? 'text-gray-400' : 'text-gray-300'}>
            {i === activeStep && <span className="inline-block w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse mr-1 align-middle" />}
            {step}
          </span>
        </span>
      ))}
    </div>
  )
}

function SkeletonCard() {
  return (
    <div className="space-y-3 animate-pulse">
      <div className="flex gap-2">
        <div className="h-5 w-20 bg-gray-200 rounded" />
        <div className="h-5 w-32 bg-gray-200 rounded" />
      </div>
      <div className="h-4 w-full bg-gray-100 rounded" />
      <div className="h-4 w-3/4 bg-gray-100 rounded" />
      <div className="h-4 w-1/2 bg-gray-100 rounded" />
    </div>
  )
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
              role="button"
              tabIndex={card?.legal_basis ? 0 : -1}
              onClick={() => card?.legal_basis && onCitationClick(card.legal_basis, idx)}
              onKeyDown={e => { if ((e.key === 'Enter' || e.key === ' ') && card?.legal_basis) { e.preventDefault(); onCitationClick(card.legal_basis, idx) } }}
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
      <ul role="listbox" aria-label="Dasar hukum" className="divide-y divide-gray-100">
        {cards.map((card, i) => (
          <li
            key={card.legal_basis || i}
            ref={el => { refs.current[i] = el }}
            role="option"
            aria-selected={focusedIndex === i}
            tabIndex={focusedIndex === i ? 0 : -1}
            onClick={() => card.legal_basis && onCitationClick(card.legal_basis)}
            onKeyDown={e => { if (e.key === 'Enter' && card.legal_basis) onCitationClick(card.legal_basis) }}
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
  const [fileLoading, setFileLoading] = useState(false)
  const [focusedHukum, setFocusedHukum] = useState<number | null>(null)
  const [panelNodeId, setPanelNodeId] = useState<string | null>(null)
  const endRef = useRef<HTMLDivElement>(null)
  const prevStatusRef = useRef<string>('')
  const transport = useMemo(() => new DefaultChatTransport({
    api: '/api/chat/ai',
    headers: () => authHeaders(),
  }), [])

  const { messages: aiMessages, sendMessage, status: chatStatus, stop } = useChat({
    transport,
    onError: (err) => {
      console.error('[useChat error]', err)
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${err.message || 'Tidak dapat terhubung ke server.'}` }])
    },
  })

  // Derive streaming state from AI SDK messages (no effects, no setState during render)
  const streamingFromAi = useMemo(() => {
    const lastAiMsg = aiMessages[aiMessages.length - 1]
    if (!lastAiMsg || lastAiMsg.role !== 'assistant') {
      return { hukum: [] as HukumCard[], perlu: [] as PerluDikonfirmasiItem[], actions: [] as ActionItem[], analisis: '', status: '' }
    }
    const parts = lastAiMsg.parts || []
    const hukum: HukumCard[] = []
    const perlu: PerluDikonfirmasiItem[] = []
    const actions: ActionItem[] = []
    let analisis = ''
    let status = ''

    for (const part of parts) {
      if (part.type === 'text') {
        analisis = part.text
      } else if (part.type.startsWith('data-')) {
        const d = (part as { type: string; data: unknown }).data as Record<string, unknown>
        if (part.type === 'data-hukum') hukum.push(d as unknown as HukumCard)
        else if (part.type === 'data-perlu') perlu.push(d as unknown as PerluDikonfirmasiItem)
        else if (part.type === 'data-action') actions.push(d as unknown as ActionItem)
        else if (part.type === 'data-status') status = (d as { text: string })?.text || ''
      }
    }
    return { hukum, perlu, actions, analisis, status }
  }, [aiMessages])

  // When stream finishes, commit to messages array
  useEffect(() => {
    if (prevStatusRef.current === 'streaming' && chatStatus === 'ready') {
      const { analisis, hukum, perlu, actions } = streamingFromAi
      if (analisis || hukum.length > 0) {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: '',
          hukum,
          analisis,
          perlu,
          actions,
        }])
      }
    }
    prevStatusRef.current = chatStatus
  }, [chatStatus, streamingFromAi])

  const loading = fileLoading || chatStatus === 'submitted' || chatStatus === 'streaming'

  const allHukum = useMemo(() => {
    const items: HukumCard[] = []
    const seen = new Set<string>()
    for (const msg of messages) {
      for (const h of (msg.hukum || [])) {
        const key = `${h.legal_basis}||${h.description}`
        if (!seen.has(key)) { seen.add(key); items.push(h) }
      }
    }
    for (const h of streamingFromAi.hukum) {
      const key = `${h.legal_basis}||${h.description}`
      if (!seen.has(key)) { seen.add(key); items.push(h) }
    }
    return items
  }, [messages, streamingFromAi.hukum])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingFromAi.analisis, streamingFromAi.perlu])

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

    const userContent = file ? `${message}\n\n📎 ${file.name}` : message
    setMessages(prev => [...prev, { role: 'user', content: userContent }])

    // File upload uses the non-streaming endpoint
    if (file) {
      setFileLoading(true)
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
          actions: response.actions,
          response_type: response.response_type,
          compliance_score: response.compliance_score,
          compliance_doc_type: response.compliance_doc_type,
          compliance_summary: response.compliance_summary,
        }])
      } catch {
        setMessages(prev => [...prev, { role: 'assistant', content: 'Gagal upload. Coba lagi.' }])
      } finally {
        setFileLoading(false)
      }
      return
    }

    // Stream via AI SDK
    sendMessage({ text: message })
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
              ) : msg.response_type === 'compliance_report' ? (
                <div className="space-y-3">
                  {/* Compliance score header */}
                  {msg.compliance_score !== undefined && (
                    <div className={`flex items-center gap-3 rounded-lg border p-3 ${msg.compliance_score >= 80 ? 'text-green-700 bg-green-100 border-green-300' : msg.compliance_score >= 50 ? 'text-amber-700 bg-amber-100 border-amber-300' : 'text-red-700 bg-red-100 border-red-300'}`}>
                      <div className={`flex items-center justify-center w-12 h-12 rounded-full ring-2 bg-white ${msg.compliance_score >= 80 ? 'ring-green-400' : msg.compliance_score >= 50 ? 'ring-amber-400' : 'ring-red-400'}`}>
                        <span className="text-lg font-bold">{msg.compliance_score}%</span>
                      </div>
                      <div>
                        <p className="text-sm font-semibold uppercase tracking-wide">{(msg.compliance_doc_type || '').replace('_', ' ')}</p>
                        {msg.compliance_summary && (
                          <p className="text-xs opacity-80">{msg.compliance_summary.compliant} sesuai · {msg.compliance_summary.violated} pelanggaran · {msg.compliance_summary.not_evaluated} tidak dievaluasi</p>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Violations */}
                  {(() => {
                    const violations = (msg.hukum || []).filter(h => h.severity === 'critical' || h.severity === 'high' || h.doc_evidence)
                    if (violations.length === 0) return null
                    return (
                      <div className="border-l-4 border-red-400 bg-red-50 rounded-r-lg p-4">
                        <h4 className="text-xs font-semibold text-red-700 uppercase tracking-wide mb-2">Pelanggaran</h4>
                        <ul className="space-y-2">
                          {violations.map((v, vi) => (
                            <li key={vi} className="flex items-start gap-2">
                              <span className="shrink-0 mt-0.5">{v.severity === 'critical' ? '🚨' : '❌'}</span>
                              <div className="min-w-0">
                                <p className="text-sm text-gray-800 font-medium">{v.description}</p>
                                {v.doc_evidence && <p className="text-xs text-red-600 mt-0.5">{v.doc_evidence}</p>}
                                {v.legal_basis && (
                                  <button onClick={() => handleCitationClick(v.legal_basis)} className="text-[10px] text-red-500 hover:underline mt-0.5">
                                    {formatPasal(v.legal_basis)}
                                  </button>
                                )}
                              </div>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )
                  })()}

                  {/* Actions */}
                  {msg.actions && msg.actions.length > 0 && (
                    <div className="border-l-4 border-orange-400 bg-orange-50 rounded-r-lg p-4">
                      <h4 className="text-xs font-semibold text-orange-700 uppercase tracking-wide mb-2">Yang Perlu Diperbaiki</h4>
                      <ul className="space-y-1.5">
                        {msg.actions.map((action, ai) => (
                          <li key={ai} className="flex items-start gap-2 text-sm">
                            <span className="text-orange-500 shrink-0">•</span>
                            <div>
                              <span className="text-gray-700">{action.description}</span>
                              {action.legal_basis && (
                                <button onClick={() => handleCitationClick(action.legal_basis)} className="ml-1.5 text-[10px] text-orange-600 hover:underline">
                                  {formatPasal(action.legal_basis)}
                                </button>
                              )}
                            </div>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Not evaluated */}
                  {msg.compliance_summary && msg.compliance_summary.not_evaluated > 0 && msg.analisis && (
                    <details className="group">
                      <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700">
                        ❓ {msg.compliance_summary.not_evaluated} item tidak dapat dievaluasi
                      </summary>
                      <div className="mt-2 pl-4 text-xs text-gray-600 whitespace-pre-line">
                        {msg.analisis.split('\n').filter(l => l.startsWith('•')).join('\n')}
                      </div>
                    </details>
                  )}

                  {/* Compliant (collapsed) */}
                  {(() => {
                    const compliant = (msg.hukum || []).filter(h => h.severity === 'low' && !h.doc_evidence)
                    if (compliant.length === 0) return null
                    return (
                      <details className="group">
                        <summary className="text-xs text-green-600 cursor-pointer hover:text-green-800">
                          ✅ {compliant.length} item sesuai ketentuan
                        </summary>
                        <ul className="mt-2 pl-4 space-y-0.5">
                          {compliant.map((c, ci) => (
                            <li key={ci} className="text-xs text-gray-600">• {c.description}</li>
                          ))}
                        </ul>
                      </details>
                    )
                  })()}
                </div>
              ) : msg.analisis ? (
                <div className="space-y-3">
                  <div className="border-l-4 border-amber-400 bg-amber-50 rounded-r-lg p-4">
                    <h4 className="text-[10px] font-semibold text-amber-700 uppercase tracking-wide mb-2">Analisis</h4>
                    <AnalisisWithCitations text={msg.analisis} hukumCards={msg.hukum || []} loading={false} onCitationClick={handleCitationClick} />
                  </div>
                  {msg.actions && msg.actions.length > 0 && (
                    <div className="border-l-4 border-orange-400 bg-orange-50 rounded-r-lg p-4">
                      <h4 className="text-xs font-semibold text-orange-700 uppercase tracking-wide mb-2">Yang Perlu Diperbaiki</h4>
                      <ul className="space-y-1.5">
                        {msg.actions.map((action, ai) => (
                          <li key={ai} className="flex items-start gap-2 text-sm">
                            <span className="text-orange-500 shrink-0">•</span>
                            <div>
                              <span className="text-gray-700">{action.description}</span>
                              {action.legal_basis && (
                                <button onClick={() => handleCitationClick(action.legal_basis)} className="ml-1.5 text-[10px] text-orange-600 hover:underline">
                                  {formatPasal(action.legal_basis)}
                                </button>
                              )}
                            </div>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
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
          <div aria-live="polite" aria-atomic={false}>
          {loading && !streamingFromAi.analisis && streamingFromAi.hukum.length === 0 && (
            <SkeletonCard />
          )}

          {loading && (chatStatus === 'submitted' || chatStatus === 'streaming') && (
            <ProgressBreadcrumb hasHukum={streamingFromAi.hukum.length > 0} hasAnalisis={!!streamingFromAi.analisis} />
          )}

          {loading && streamingFromAi.analisis && (
            <div className="border-l-4 border-amber-400 bg-amber-50 rounded-r-lg p-4 animate-[fadeIn_0.2s_ease-out]">
              <h4 className="text-[10px] font-semibold text-amber-700 uppercase tracking-wide mb-2">Analisis</h4>
              <AnalisisWithCitations text={streamingFromAi.analisis} hukumCards={streamingFromAi.hukum} loading={true} onCitationClick={handleCitationClick} />
            </div>
          )}

          {loading && streamingFromAi.perlu.length > 0 && (
            <div className="animate-[fadeIn_0.2s_ease-out]">
              <PerluSection items={streamingFromAi.perlu} onSubmit={handleSend} />
            </div>
          )}

          {loading && streamingFromAi.actions.length > 0 && (
            <div className="border-l-4 border-orange-400 bg-orange-50 rounded-r-lg p-4 animate-[fadeIn_0.2s_ease-out]">
              <h4 className="text-xs font-semibold text-orange-700 uppercase tracking-wide mb-2">Yang Perlu Diperbaiki</h4>
              <ul className="space-y-1.5">
                {streamingFromAi.actions.map((action, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm">
                    <span className="text-orange-500 shrink-0">•</span>
                    <div>
                      <span className="text-gray-700">{action.description}</span>
                      {action.legal_basis && (
                        <button onClick={() => handleCitationClick(action.legal_basis)} className="ml-1.5 text-[10px] text-orange-600 hover:underline">
                          {formatPasal(action.legal_basis)}
                        </button>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
          </div>{/* end aria-live */}

          <div ref={endRef} />
        </div>
      </div>

      {/* Input — with file attachment */}
      <div className="border-t border-gray-200 bg-white px-4 py-3 pb-safe" style={{ paddingRight: hasSidebar && !panelNodeId ? '21rem' : panelNodeId ? '25rem' : undefined }}>
        <div className="max-w-3xl mx-auto flex items-center gap-2">
          <div className="flex-1">
            <ChatInput onSend={handleSend} disabled={loading} />
          </div>
          {(chatStatus === 'submitted' || chatStatus === 'streaming') && (
            <button onClick={() => stop()} className="shrink-0 rounded border border-gray-300 px-3 py-2 text-xs text-gray-600 hover:bg-gray-100">Stop</button>
          )}
        </div>
      </div>

      {/* Sidebar — hukum cards stream here */}
      <HukumSidebarLab cards={allHukum} focusedIndex={focusedHukum} onCitationClick={handleCitationClick} />

      {/* Provision panel — opens when clicking sidebar card or superscript */}
      <ProvisionPanel nodeId={panelNodeId} onClose={() => setPanelNodeId(null)} />
    </div>
  )
}
