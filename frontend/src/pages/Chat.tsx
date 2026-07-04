import { useState, useRef, useEffect, useMemo, useCallback } from 'react'
import { sendMessageWithFile, sendMessageStream } from '../api'
import type { Message, HukumItem, ChatResponseBody } from '../types'
import ChatInput from '../components/chat/ChatInput'
import ChatMessage from '../components/chat/ChatMessage'
import ThreeSpaceResponse from '../components/chat/ThreeSpaceResponse'
import QuickActions from '../components/chat/QuickActions'
import ThreeSpaceSkeleton from '../components/chat/ThreeSpaceSkeleton'
import ProvisionPanel from '../components/shared/ProvisionPanel'
import HukumSidebar from '../components/shared/HukumSidebar'
import Markdown from '../components/shared/Markdown'

function useIsDesktop() {
  const [isDesktop, setIsDesktop] = useState(() => window.matchMedia('(min-width: 768px)').matches)
  useEffect(() => {
    const mq = window.matchMedia('(min-width: 768px)')
    const handler = (e: MediaQueryListEvent) => setIsDesktop(e.matches)
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [])
  return isDesktop
}

function StreamingBlocks({ text }: { text: string }) {
  const blocks = text.split(/\n\n+/)
  const pending = blocks.pop() || ''
  return (
    <div className="text-sm text-gray-700 space-y-2">
      {blocks.map((block, i) => (
        <p key={i} className="whitespace-pre-line"><Markdown text={block} /></p>
      ))}
      {pending && (
        <p className="whitespace-pre-line opacity-90">{pending}</p>
      )}
    </div>
  )
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [sessionId, setSessionId] = useState<string>()
  const [loading, setLoading] = useState(false)
  const [streamingText, setStreamingText] = useState('')
  const [panelNodeId, setPanelNodeId] = useState<string | null>(null)
  const [focusedHukum, setFocusedHukum] = useState<number | null>(null)
  const endRef = useRef<HTMLDivElement>(null)
  const bufferRef = useRef('')
  const rafRef = useRef<number | null>(null)

  const flushBuffer = useCallback(() => {
    setStreamingText(bufferRef.current)
    rafRef.current = null
  }, [])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const allHukum = useMemo(() => {
    const items: HukumItem[] = []
    const seen = new Set<string>()
    for (const msg of messages) {
      if (msg.role === 'assistant' && msg.response) {
        for (const item of msg.response.hukum) {
          const key = `${item.legal_basis}||${item.description}`
          if (!seen.has(key)) {
            seen.add(key)
            items.push(item)
          }
        }
      }
    }
    return items
  }, [messages])

  function getHukumOffset(msgIndex: number): number {
    let offset = 0
    for (let i = 0; i < msgIndex; i++) {
      const msg = messages[i]
      if (msg.role === 'assistant' && msg.response) {
        offset += msg.response.hukum.length
      }
    }
    return offset
  }

  async function handleSend(text: string, file?: File) {
    const userMsg: Message = {
      role: 'user',
      content: file ? `${text}\n\n📎 ${file.name}` : text,
      timestamp: Date.now(),
    }
    setMessages(prev => [...prev, userMsg])
    setLoading(true)
    bufferRef.current = ''
    setStreamingText('')

    try {
      if (file) {
        const res = await sendMessageWithFile(text, file, sessionId)
        setSessionId(res.session_id)
        const assistantMsg: Message = {
          role: 'assistant',
          content: '',
          response: res.response,
          timestamp: Date.now(),
        }
        setMessages(prev => [...prev, assistantMsg])
      } else {
        await sendMessageStream(text, {
          onStatus: () => {},
          onToken: (t) => {
            bufferRef.current += t
            if (!rafRef.current) {
              rafRef.current = requestAnimationFrame(flushBuffer)
            }
          },
          onComplete: (data, sid) => {
            setSessionId(sid)
            if (rafRef.current) { cancelAnimationFrame(rafRef.current); rafRef.current = null }
            bufferRef.current = ''
            setStreamingText('')
            const response: ChatResponseBody = {
              response_type: 'chat',
              hukum: ((data.hukum as unknown[]) || []).map((h: unknown) => {
                const item = h as Record<string, string>
                return { description: item.description || '', legal_basis: item.legal_basis || '', severity: (item.severity || 'medium') as 'critical'|'high'|'medium'|'low' }
              }),
              analisis: data.analisis ? { text: data.analisis as string, disclaimer: 'Interpretasi — bukan hukum. Hasil di pengadilan bisa berbeda.' } : null,
              perlu_dikonfirmasi: ((data.perlu_dikonfirmasi as unknown[]) || []).map((q: unknown) => {
                const item = q as Record<string, unknown>
                return { question: item.question as string || '', why: item.why as string || '', options: item.options as string[] | undefined, parameter_key: item.key as string || '', type: (item.type as 'select'|'number'|'text'|'file') || 'text' }
              }),
              actions: [],
            }
            const assistantMsg: Message = {
              role: 'assistant',
              content: '',
              response,
              timestamp: Date.now(),
            }
            setMessages(prev => [...prev, assistantMsg])
          },
          onError: () => {
            if (rafRef.current) { cancelAnimationFrame(rafRef.current); rafRef.current = null }
            bufferRef.current = ''
            setStreamingText('')
            const errMsg: Message = {
              role: 'assistant',
              content: 'Tidak dapat memproses. Coba lagi.',
              timestamp: Date.now(),
            }
            setMessages(prev => [...prev, errMsg])
          },
        }, sessionId)
      }
    } catch {
      const errMsg: Message = {
        role: 'assistant',
        content: 'Tidak dapat memproses. Coba lagi.',
        timestamp: Date.now(),
      }
      setMessages(prev => [...prev, errMsg])
    } finally {
      setLoading(false)
    }
  }

  function handleCitationFocus(index: number) {
    setFocusedHukum(index)
    setTimeout(() => setFocusedHukum(null), 2000)
  }

  const hasSidebar = allHukum.length > 0
  const isDesktop = useIsDesktop()

  const contentPadRight = isDesktop ? (hasSidebar && !panelNodeId ? '21rem' : panelNodeId ? '25rem' : undefined) : undefined

  return (
    <div className="flex flex-col h-[calc(100vh-57px)]">
      <div className="flex-1 overflow-y-auto px-4 py-6"
           style={{ paddingRight: contentPadRight }}>
        <div className="max-w-3xl mx-auto space-y-4">
          {messages.length === 0 && (
            <div className="mt-20 text-center">
              <h1 className="text-2xl font-semibold text-gray-900 mb-2">Tanya HR Compliance</h1>
              <p className="text-gray-500 mb-8">17 regulasi · 5.676 pasal · 38 provinsi</p>
              <QuickActions onSelect={handleSend} />
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i}>
              {msg.role === 'user' ? (
                <ChatMessage
                  role="user"
                  content={msg.content}
                  onRetry={() => {
                    const text = msg.content.split('\n\n📎')[0]
                    setMessages(prev => prev.slice(0, i))
                    setTimeout(() => handleSend(text), 0)
                  }}
                />
              ) : msg.response ? (
                <ThreeSpaceResponse
                  response={msg.response}
                  onPrefill={handleSend}
                  onCitationFocus={handleCitationFocus}
                  onCitationClick={setPanelNodeId}
                  hukumOffset={getHukumOffset(i)}
                />
              ) : (
                <ChatMessage role="assistant" content={msg.content} />
              )}
            </div>
          ))}

          {loading && streamingText && (
            <div className="border-l-4 border-amber-400 bg-amber-50 rounded-r-lg p-4 relative overflow-hidden">
              <div className="absolute top-0 left-0 right-0 h-0.5">
                <div className="h-full bg-gradient-to-r from-amber-300 via-amber-500 to-amber-300 animate-[shimmer_2s_ease-in-out_infinite]" style={{ backgroundSize: '200% 100%' }} />
              </div>
              <div className="flex items-center gap-2 mb-2">
                <div className="flex gap-0.5">
                  <span className="w-1 h-1 rounded-full bg-amber-500 animate-[bounce_1.4s_ease-in-out_infinite]" />
                  <span className="w-1 h-1 rounded-full bg-amber-500 animate-[bounce_1.4s_ease-in-out_0.2s_infinite]" />
                  <span className="w-1 h-1 rounded-full bg-amber-500 animate-[bounce_1.4s_ease-in-out_0.4s_infinite]" />
                </div>
                <h4 className="text-xs font-semibold text-amber-700 uppercase tracking-wide">Analisis</h4>
              </div>
              <StreamingBlocks text={streamingText} />
            </div>
          )}

          {loading && !streamingText && <ThreeSpaceSkeleton />}

          <div ref={endRef} />
        </div>
      </div>

      <div className="border-t border-gray-200 bg-white px-4 py-3 pb-safe"
           style={{ paddingRight: contentPadRight }}>
        <div className="max-w-3xl mx-auto">
          <ChatInput onSend={handleSend} disabled={loading} />
        </div>
      </div>

      <HukumSidebar
        items={allHukum}
        focusedIndex={focusedHukum}
        onCitationClick={setPanelNodeId}
      />

      <ProvisionPanel nodeId={panelNodeId} onClose={() => setPanelNodeId(null)} />
    </div>
  )
}
