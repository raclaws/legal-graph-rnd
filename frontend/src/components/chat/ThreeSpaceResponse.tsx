import { useState, useMemo } from 'react'
import type { ChatResponseBody, PerluDikonfirmasiItem } from '../../types'
import Markdown from '../shared/Markdown'

interface Props {
  response: ChatResponseBody
  onPrefill: (text: string) => void
  onCitationFocus?: (index: number) => void
  onCitationClick?: (nodeId: string) => void
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

interface TextSegment {
  text: string
  footnote?: number
}

function parseFootnoteMarkers(text: string): TextSegment[] {
  // Split on [1], [2], [3] etc — LLM inserts these as citation markers
  const parts = text.split(/\[(\d+)\]/)
  const segments: TextSegment[] = []
  for (let i = 0; i < parts.length; i++) {
    if (i % 2 === 0) {
      if (parts[i]) segments.push({ text: parts[i] })
    } else {
      segments.push({ text: '', footnote: parseInt(parts[i], 10) })
    }
  }
  return segments
}

function ComplianceScorecard({ response, onCitationClick }: { response: ChatResponseBody; onCitationClick?: (nodeId: string) => void }) {
  const score = response.compliance_score ?? 0
  const docType = response.compliance_doc_type ?? ''
  const summary = response.compliance_summary ?? { compliant: 0, violated: 0, not_evaluated: 0 }

  const violations = response.hukum.filter(h => h.severity === 'critical' || h.severity === 'high' || (h.doc_evidence))
  const compliant = response.hukum.filter(h => h.severity === 'low' && !h.doc_evidence)
  const unclear = summary.not_evaluated

  const scoreColor = score >= 80 ? 'text-green-700 bg-green-100 border-green-300' : score >= 50 ? 'text-amber-700 bg-amber-100 border-amber-300' : 'text-red-700 bg-red-100 border-red-300'
  const scoreRing = score >= 80 ? 'ring-green-400' : score >= 50 ? 'ring-amber-400' : 'ring-red-400'

  return (
    <div className="space-y-3">
      {/* Score header */}
      <div className={`flex items-center gap-3 rounded-lg border p-3 ${scoreColor}`}>
        <div className={`flex items-center justify-center w-12 h-12 rounded-full ring-2 ${scoreRing} bg-white`}>
          <span className="text-lg font-bold">{score}%</span>
        </div>
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide">{docType.replace('_', ' ')}</p>
          <p className="text-xs opacity-80">{summary.compliant} sesuai · {summary.violated} pelanggaran · {unclear} tidak dievaluasi</p>
        </div>
      </div>

      {/* Violations */}
      {violations.length > 0 && (
        <div className="border-l-4 border-red-400 bg-red-50 rounded-r-lg p-4">
          <h4 className="text-xs font-semibold text-red-700 uppercase tracking-wide mb-2">Pelanggaran</h4>
          <ul className="space-y-2">
            {violations.map((v, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="shrink-0 mt-0.5">{v.severity === 'critical' ? '🚨' : '❌'}</span>
                <div className="min-w-0">
                  <p className="text-sm text-gray-800 font-medium">{v.description}</p>
                  {v.doc_evidence && <p className="text-xs text-red-600 mt-0.5">{v.doc_evidence}</p>}
                  {v.legal_basis && (
                    <button
                      onClick={() => onCitationClick?.(v.legal_basis)}
                      className="text-[10px] text-red-500 hover:underline mt-0.5"
                    >
                      {formatPasal(v.legal_basis)}
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Actions */}
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
                      onClick={() => onCitationClick?.(action.legal_basis)}
                      className="ml-1.5 text-[10px] text-orange-600 hover:underline"
                    >
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
      {unclear > 0 && response.analisis && (
        <details className="group">
          <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700">
            ❓ {unclear} item tidak dapat dievaluasi
          </summary>
          <div className="mt-2 pl-4 text-xs text-gray-600 whitespace-pre-line">
            {response.analisis.text.split('\n').filter(l => l.startsWith('•')).join('\n')}
          </div>
        </details>
      )}

      {/* Compliant (collapsed) */}
      {compliant.length > 0 && (
        <details className="group">
          <summary className="text-xs text-green-600 cursor-pointer hover:text-green-800">
            ✅ {compliant.length} item sesuai ketentuan
          </summary>
          <ul className="mt-2 pl-4 space-y-0.5">
            {compliant.map((c, i) => (
              <li key={i} className="text-xs text-gray-600">• {c.description}</li>
            ))}
          </ul>
        </details>
      )}
    </div>
  )
}

export default function ThreeSpaceResponse({ response, onPrefill, onCitationFocus, onCitationClick, hukumOffset = 0, showUnclear }: Props) {
  if (response.response_type === 'compliance_report') {
    return <ComplianceScorecard response={response} onCitationClick={onCitationClick} />
  }

  const { hukum, analisis, perlu_dikonfirmasi } = response
  const hasBlocking = perlu_dikonfirmasi.length > 0

  const analisisSegments = useMemo(() => {
    if (!analisis?.text) return []
    return parseFootnoteMarkers(analisis.text)
  }, [analisis])

  return (
    <div className="space-y-3">
      {perlu_dikonfirmasi.length > 0 && (
        <PerluSection items={perlu_dikonfirmasi} onSubmit={onPrefill} />
      )}

      {analisis && !hasBlocking && (
        <div className="border-l-4 border-amber-400 bg-amber-50 rounded-r-lg p-4">
          <h4 className="text-xs font-semibold text-amber-700 uppercase tracking-wide mb-1">Analisis</h4>
          <p className="text-xs text-gray-500 italic mb-2">{analisis.disclaimer}</p>
          <p className="text-sm text-gray-700 whitespace-pre-line">
            {analisisSegments.map((seg, i) => {
              if (seg.footnote) {
                const idx = seg.footnote - 1
                if (idx >= hukum.length) return null
                const item = hukum[idx]
                return (
                  <sup
                    key={i}
                    onClick={() => {
                      onCitationFocus?.(hukumOffset + idx)
                      if (item.legal_basis) onCitationClick?.(item.legal_basis)
                    }}
                    className={`font-semibold text-[9px] ml-0.5 ${item.legal_basis ? 'text-blue-600 cursor-pointer hover:text-blue-800' : 'text-gray-400 cursor-default'}`}
                  >
                    {seg.footnote}
                  </sup>
                )
              }
              return <span key={i}><Markdown text={seg.text} /></span>
            })}
          </p>
        </div>
      )}

      {/* Footnote sources */}
      {hukum.length > 0 && (
        <div className="px-1 pt-2">
          <p className="text-[10px] text-gray-400 uppercase tracking-wide mb-1">Sumber</p>
          <ol className="list-none flex flex-wrap gap-x-3 gap-y-0.5">
            {hukum.map((item, i) => (
              <li key={i}>
                {item.legal_basis ? (
                  <button
                    onClick={() => {
                      onCitationFocus?.(hukumOffset + i)
                      onCitationClick?.(item.legal_basis)
                    }}
                    className="text-[11px] text-blue-600 hover:text-blue-800 font-medium hover:underline"
                  >
                    <sup className="text-[9px]">{i + 1}</sup> {formatPasal(item.legal_basis)}
                  </button>
                ) : (
                  <span className="text-[11px] text-gray-400 font-medium">
                    <sup className="text-[9px]">{i + 1}</sup> {item.description.slice(0, 40)}{item.description.length > 40 ? '…' : ''}
                  </span>
                )}
              </li>
            ))}
          </ol>
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
                      onClick={() => onCitationClick?.(action.legal_basis)}
                      className="ml-1.5 text-[10px] text-orange-600 hover:underline"
                    >
                      {formatPasal(action.legal_basis)}
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
