import { useState, useRef, useEffect, useMemo } from 'react'
import { sendMessage, sendMessageWithFile } from '../api'
import type { Message, HukumItem } from '../types'
import ChatInput from '../components/chat/ChatInput'
import ChatMessage from '../components/chat/ChatMessage'
import ThreeSpaceResponse from '../components/chat/ThreeSpaceResponse'
import QuickActions from '../components/chat/QuickActions'
import ThreeSpaceSkeleton from '../components/chat/ThreeSpaceSkeleton'
import ProvisionPanel from '../components/shared/ProvisionPanel'
import HukumSidebar from '../components/shared/HukumSidebar'

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [sessionId, setSessionId] = useState<string>()
  const [loading, setLoading] = useState(false)
  const [panelNodeId, setPanelNodeId] = useState<string | null>(null)
  const [focusedHukum, setFocusedHukum] = useState<number | null>(null)
  const endRef = useRef<HTMLDivElement>(null)

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

    try {
      const res = file
        ? await sendMessageWithFile(text, file, sessionId)
        : await sendMessage(text, sessionId)
      setSessionId(res.session_id)

      const assistantMsg: Message = {
        role: 'assistant',
        content: '',
        response: res.response,
        timestamp: Date.now(),
      }
      setMessages(prev => [...prev, assistantMsg])
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

  return (
    <div className="flex flex-col h-[calc(100vh-57px)]">
      <div className={`flex-1 overflow-y-auto px-4 py-6 ${hasSidebar ? 'pr-84' : ''} ${panelNodeId ? 'pr-[25rem]' : ''}`}
           style={hasSidebar && !panelNodeId ? { paddingRight: '21rem' } : panelNodeId ? { paddingRight: '25rem' } : {}}>
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
                <ChatMessage role="user" content={msg.content} />
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

          {loading && <ThreeSpaceSkeleton />}

          <div ref={endRef} />
        </div>
      </div>

      <div className={`border-t border-gray-200 bg-white px-4 py-3`}
           style={hasSidebar && !panelNodeId ? { paddingRight: '21rem' } : panelNodeId ? { paddingRight: '25rem' } : {}}>
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
