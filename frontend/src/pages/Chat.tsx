import { useState, useRef, useEffect } from 'react'
import { sendMessage } from '../api'
import type { Message } from '../types'
import ChatInput from '../components/chat/ChatInput'
import ChatMessage from '../components/chat/ChatMessage'
import ThreeSpaceResponse from '../components/chat/ThreeSpaceResponse'
import QuickActions from '../components/chat/QuickActions'

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [sessionId, setSessionId] = useState<string>()
  const [loading, setLoading] = useState(false)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function handleSend(text: string) {
    const userMsg: Message = { role: 'user', content: text, timestamp: Date.now() }
    setMessages(prev => [...prev, userMsg])
    setLoading(true)

    try {
      const res = await sendMessage(text, sessionId)
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

  return (
    <div className="flex flex-col h-[calc(100vh-57px)]">
      <div className="flex-1 overflow-y-auto px-4 py-6">
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
                <ThreeSpaceResponse response={msg.response} onPrefill={handleSend} />
              ) : (
                <ChatMessage role="assistant" content={msg.content} />
              )}
            </div>
          ))}

          {loading && (
            <div className="flex gap-2 items-center text-gray-400 text-sm py-4">
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse" />
              Memproses...
            </div>
          )}

          <div ref={endRef} />
        </div>
      </div>

      <div className="border-t border-gray-200 bg-white px-4 py-3">
        <div className="max-w-3xl mx-auto">
          <ChatInput onSend={handleSend} disabled={loading} />
        </div>
      </div>
    </div>
  )
}
