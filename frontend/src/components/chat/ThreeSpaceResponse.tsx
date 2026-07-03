import { useState } from 'react'
import type { ChatResponseBody, PerluDikonfirmasiItem } from '../../types'
import SeverityBadge from '../shared/SeverityBadge'

interface Props {
  response: ChatResponseBody
  onPrefill: (text: string) => void
  onCitationClick?: (nodeId: string) => void
}

function PerluItem({ q, onAnswer }: { q: PerluDikonfirmasiItem; onAnswer: (answer: string) => void }) {
  const [value, setValue] = useState('')

  if (q.type === 'select' && q.options) {
    return (
      <div className="px-2 py-1.5">
        <p className="text-sm font-medium text-gray-700">{q.question}</p>
        {q.why && <p className="text-xs text-gray-500 mt-0.5">{q.why}</p>}
        <div className="flex flex-wrap gap-1.5 mt-2">
          {q.options.map((opt, i) => (
            <button
              key={i}
              onClick={() => onAnswer(`${q.question}: ${opt}`)}
              className="rounded-full border border-red-200 px-3 py-1 text-xs text-gray-700 hover:bg-red-100 hover:border-red-400 transition-colors"
            >
              {opt}
            </button>
          ))}
        </div>
      </div>
    )
  }

  if (q.type === 'number') {
    return (
      <div className="px-2 py-1.5">
        <p className="text-sm font-medium text-gray-700">{q.question}</p>
        {q.why && <p className="text-xs text-gray-500 mt-0.5">{q.why}</p>}
        <div className="flex gap-2 mt-2">
          <input
            type="number"
            value={value}
            onChange={e => setValue(e.target.value)}
            placeholder="0"
            className="rounded border border-gray-300 px-2 py-1 text-sm w-32 focus:outline-none focus:ring-1 focus:ring-red-400"
          />
          <button
            onClick={() => value && onAnswer(`${q.question}: ${value}`)}
            disabled={!value}
            className="rounded bg-red-600 px-3 py-1 text-xs text-white hover:bg-red-700 disabled:opacity-30"
          >
            Jawab
          </button>
        </div>
      </div>
    )
  }

  return (
    <button
      onClick={() => onAnswer(q.question)}
      className="block w-full text-left text-sm text-gray-700 hover:bg-red-100 rounded px-2 py-1.5 transition-colors"
    >
      <span className="font-medium">{q.question}</span>
      {q.why && <span className="block text-xs text-gray-500 mt-0.5">{q.why}</span>}
    </button>
  )
}

export default function ThreeSpaceResponse({ response, onPrefill, onCitationClick }: Props) {
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

      {hukum.length > 0 && (
        <div className="border-l-4 border-blue-400 bg-blue-50 rounded-r-lg p-4">
          <h4 className="text-xs font-semibold text-blue-700 uppercase tracking-wide mb-2">Hukum</h4>
          <ul className="space-y-1.5">
            {hukum.map((item, i) => (
              <li key={i} className="flex items-start gap-2 text-sm">
                <SeverityBadge severity={item.severity} />
                <span className="text-gray-700">{item.description}</span>
                {item.legal_basis && (
                  <button
                    onClick={() => onCitationClick?.(item.legal_basis)}
                    className="text-xs text-blue-600 shrink-0 hover:underline cursor-pointer"
                  >
                    {item.legal_basis}
                  </button>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {analisis && !hasBlocking && (
        <div className="border-l-4 border-amber-400 bg-amber-50 rounded-r-lg p-4">
          <h4 className="text-xs font-semibold text-amber-700 uppercase tracking-wide mb-1">Analisis</h4>
          <p className="text-xs text-gray-500 italic mb-2">{analisis.disclaimer}</p>
          <p className="text-sm text-gray-700 whitespace-pre-line">{analisis.text}</p>
        </div>
      )}
    </div>
  )
}
