import { useState } from 'react'
import type { ChatResponseBody, PerluDikonfirmasiItem } from '../../types'

interface Props {
  response: ChatResponseBody
  onPrefill: (text: string) => void
  onCitationFocus?: (index: number) => void
  hukumOffset?: number
  showUnclear?: boolean
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

  function handleCancel() {
    setValues({})
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
    <div className="border-l-4 border-red-400 bg-red-50 rounded-r-lg p-4">
      <h4 className="text-xs font-semibold text-red-700 uppercase tracking-wide mb-3">Perlu Dikonfirmasi</h4>
      <div className="space-y-3">
        {items.map((q, i) => {
          const key = q.parameter_key || q.question
          return (
            <div key={i} className="bg-white rounded border border-red-100 p-3">
              <p className="text-sm font-medium text-gray-700">{q.question}</p>
              {q.why && <p className="text-xs text-gray-500 mt-0.5 mb-2">{q.why}</p>}

              {q.type === 'select' && q.options ? (
                <div className="flex flex-wrap gap-1.5 mt-1">
                  {q.options.map((opt, j) => (
                    <button
                      key={j}
                      onClick={() => setValue(key, opt)}
                      className={`rounded-full border px-3 py-1 text-xs transition-colors ${values[key] === opt ? 'border-red-500 bg-red-100 text-red-700 font-medium' : 'border-gray-200 text-gray-600 hover:bg-gray-100'}`}
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
                  className="mt-1 rounded border border-gray-300 px-2 py-1.5 text-sm w-full focus:outline-none focus:ring-1 focus:ring-red-400"
                />
              ) : (
                <input
                  type="text"
                  value={values[key] || ''}
                  onChange={e => setValue(key, e.target.value)}
                  placeholder="Ketik jawaban..."
                  className="mt-1 rounded border border-gray-300 px-2 py-1.5 text-sm w-full focus:outline-none focus:ring-1 focus:ring-red-400"
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
          className="rounded bg-red-600 px-4 py-1.5 text-xs font-medium text-white hover:bg-red-700 disabled:opacity-30"
        >
          Kirim ({filledCount}/{items.length})
        </button>
        <button
          onClick={handleCancel}
          className="rounded border border-gray-300 px-4 py-1.5 text-xs text-gray-600 hover:bg-gray-100"
        >
          Batal
        </button>
      </div>

      <p className="text-xs text-gray-500 mt-2 italic">Analisis lengkap setelah pertanyaan di atas dijawab.</p>
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
        <PerluSection items={perlu_dikonfirmasi} onSubmit={onPrefill} />
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
