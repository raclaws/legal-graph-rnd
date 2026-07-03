import type { ChatResponseBody } from '../../types'
import SeverityBadge from '../shared/SeverityBadge'

interface Props {
  response: ChatResponseBody
  onPrefill: (text: string) => void
}

export default function ThreeSpaceResponse({ response, onPrefill }: Props) {
  const { hukum, analisis, perlu_dikonfirmasi } = response
  const hasBlocking = perlu_dikonfirmasi.length > 0

  return (
    <div className="space-y-3">
      {/* Perlu Dikonfirmasi — shown first if present */}
      {perlu_dikonfirmasi.length > 0 && (
        <div className="border-l-4 border-red-400 bg-red-50 rounded-r-lg p-4">
          <h4 className="text-xs font-semibold text-red-700 uppercase tracking-wide mb-2">Perlu Dikonfirmasi</h4>
          <div className="space-y-2">
            {perlu_dikonfirmasi.map((q, i) => (
              <button
                key={i}
                onClick={() => onPrefill(q.question)}
                className="block w-full text-left text-sm text-gray-700 hover:bg-red-100 rounded px-2 py-1.5 transition-colors"
              >
                <span className="font-medium">{q.question}</span>
                {q.why && <span className="block text-xs text-gray-500 mt-0.5">{q.why}</span>}
              </button>
            ))}
          </div>
          {hasBlocking && (
            <p className="text-xs text-gray-500 mt-2 italic">Analisis lengkap setelah pertanyaan di atas dijawab.</p>
          )}
        </div>
      )}

      {/* Hukum */}
      {hukum.length > 0 && (
        <div className="border-l-4 border-blue-400 bg-blue-50 rounded-r-lg p-4">
          <h4 className="text-xs font-semibold text-blue-700 uppercase tracking-wide mb-2">Hukum</h4>
          <ul className="space-y-1.5">
            {hukum.map((item, i) => (
              <li key={i} className="flex items-start gap-2 text-sm">
                <SeverityBadge severity={item.severity} />
                <span className="text-gray-700">{item.description}</span>
                {item.legal_basis && (
                  <span className="text-xs text-blue-600 shrink-0">{item.legal_basis}</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Analisis — suppressed if blocking questions present */}
      {analisis && !hasBlocking && (
        <div className="border-l-4 border-amber-400 bg-amber-50 rounded-r-lg p-4">
          <h4 className="text-xs font-semibold text-amber-700 uppercase tracking-wide mb-1">Analisis</h4>
          <p className="text-xs text-gray-500 italic mb-2">{analisis.disclaimer}</p>
          <p className="text-sm text-gray-700">{analisis.text}</p>
        </div>
      )}
    </div>
  )
}
