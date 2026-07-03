import { useState } from 'react'
import type { ChatResponseBody, PerluDikonfirmasiItem } from '../../types'

interface Props {
  response: ChatResponseBody
  onPrefill: (text: string) => void
  onCitationFocus?: (index: number) => void
  hukumOffset?: number
  showUnclear?: boolean
}

function PerluItem({ q, onAnswer }: { q: PerluDikonfirmasiItem; onAnswer: (answer: string) => void }) {
  const [expanded, setExpanded] = useState(false)
  const [value, setValue] = useState('')

  function handleSubmit() {
    if (!value.trim()) return
    onAnswer(`${q.question}: ${value.trim()}`)
    setValue('')
    setExpanded(false)
  }

  function handleCancel() {
    setValue('')
    setExpanded(false)
  }

  if (!expanded) {
    return (
      <button
        onClick={() => setExpanded(true)}
        className="block w-full text-left text-sm text-gray-700 hover:bg-red-100 rounded px-2 py-1.5 transition-colors"
      >
        <span className="font-medium">{q.question}</span>
        {q.why && <span className="block text-xs text-gray-500 mt-0.5">{q.why}</span>}
      </button>
    )
  }

  return (
    <div className="px-2 py-2 bg-white rounded border border-red-200">
      <p className="text-sm font-medium text-gray-700 mb-2">{q.question}</p>
      {q.why && <p className="text-xs text-gray-500 mb-2">{q.why}</p>}

      {q.type === 'select' && q.options ? (
        <div className="flex flex-wrap gap-1.5 mb-2">
          {q.options.map((opt, i) => (
            <button
              key={i}
              onClick={() => setValue(opt)}
              className={`rounded-full border px-3 py-1 text-xs transition-colors ${value === opt ? 'border-red-500 bg-red-100 text-red-700 font-medium' : 'border-gray-200 text-gray-700 hover:bg-gray-100'}`}
            >
              {opt}
            </button>
          ))}
        </div>
      ) : q.type === 'number' ? (
        <input
          type="number"
          value={value}
          onChange={e => setValue(e.target.value)}
          placeholder="0"
          className="rounded border border-gray-300 px-2 py-1.5 text-sm w-full mb-2 focus:outline-none focus:ring-1 focus:ring-red-400"
        />
      ) : (
        <input
          type="text"
          value={value}
          onChange={e => setValue(e.target.value)}
          placeholder="Ketik jawaban..."
          className="rounded border border-gray-300 px-2 py-1.5 text-sm w-full mb-2 focus:outline-none focus:ring-1 focus:ring-red-400"
          onKeyDown={e => { if (e.key === 'Enter') handleSubmit() }}
        />
      )}

      <div className="flex gap-2">
        <button
          onClick={handleSubmit}
          disabled={!value.trim()}
          className="rounded bg-red-600 px-3 py-1 text-xs text-white hover:bg-red-700 disabled:opacity-30"
        >
          Kirim
        </button>
        <button
          onClick={handleCancel}
          className="rounded border border-gray-300 px-3 py-1 text-xs text-gray-600 hover:bg-gray-100"
        >
          Batal
        </button>
      </div>
    </div>
  )
}

function formatPasal(nodeId: string): string {
  const m = nodeId.match(/^(\w+)\/(\d+)\/(\d+)\/.*?Pasal\/(\d+\w*)/)
  if (m) return `${m[1]} ${m[3]}/${m[2]} Ps. ${m[4]}`
  return nodeId
}

export default function ThreeSpaceResponse({ response, onPrefill, onCitationFocus, hukumOffset = 0, showUnclear }: Props) {
  const { hukum, analisis, perlu_dikonfirmasi } = response
  const hasBlocking = perlu_dikonfirmasi.length > 0

  return (
    <div className="space-y-3">
      {perlu_dikonfirmasi.length > 0 && (
        <div className="border-l-4 border-red-400 bg-red-50 rounded-r-lg p-4">
          <h4 className="text-xs font-semibold text-red-700 uppercase tracking-wide mb-2">Perlu Dikonfirmasi</h4>
          <div className="space-y-2">
            {perlu_dikonfirmasi.map((q, i) => (
              <PerluItem key={i} q={q} onAnswer={onPrefill} />
            ))}
          </div>
          {hasBlocking && (
            <p className="text-xs text-gray-500 mt-2 italic">Analisis lengkap setelah pertanyaan di atas dijawab.</p>
          )}
        </div>
      )}

      {/* Citation links — click to focus in sidebar */}
      {hukum.length > 0 && (
        <div className="flex flex-wrap gap-1.5 px-1">
          {hukum.map((item, i) => (
            <button
              key={i}
              onClick={() => onCitationFocus?.(hukumOffset + i)}
              className="inline-flex items-center gap-1 rounded border border-blue-200 bg-blue-50 px-2 py-0.5 text-[10px] text-blue-700 hover:bg-blue-100 hover:border-blue-400 transition-colors"
            >
              <span className="font-medium">{formatPasal(item.legal_basis || 'Ref')}</span>
            </button>
          ))}
        </div>
      )}

      {analisis && !hasBlocking && (
        <div className="border-l-4 border-amber-400 bg-amber-50 rounded-r-lg p-4">
          <h4 className="text-xs font-semibold text-amber-700 uppercase tracking-wide mb-1">Analisis</h4>
          <p className="text-xs text-gray-500 italic mb-2">{analisis.disclaimer}</p>
          <p className="text-sm text-gray-700 whitespace-pre-line">{analisis.text}</p>
        </div>
      )}

      {response.actions && response.actions.length > 0 && (
        <div className="border-l-4 border-orange-400 bg-orange-50 rounded-r-lg p-4">
          <h4 className="text-xs font-semibold text-orange-700 uppercase tracking-wide mb-2">Yang Perlu Diperbaiki</h4>
          <ul className="space-y-1.5">
            {response.actions.map((action, i) => (
              <li key={i} className="flex items-start gap-2 text-sm">
                <span className="text-orange-500 shrink-0">•</span>
                <div>
                  <span className="text-gray-700">{action.description}</span>
                  {action.legal_basis && (
                    <button
                      onClick={() => onCitationFocus?.(i)}
                      className="ml-1.5 text-[10px] text-orange-600 hover:underline"
                    >
                      {action.legal_basis}
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
