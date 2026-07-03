import { useState, useEffect } from 'react'
import { getProvision } from '../../api'
import type { ProvisionResponse } from '../../types'

interface Props {
  nodeId: string | null
  onClose: () => void
}

export default function ProvisionPanel({ nodeId, onClose }: Props) {
  const [data, setData] = useState<ProvisionResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!nodeId) { setData(null); return }
    setLoading(true)
    setError(null)
    getProvision(nodeId)
      .then(setData)
      .catch(() => setError('Tidak dapat memuat data pasal.'))
      .finally(() => setLoading(false))
  }, [nodeId])

  if (!nodeId) return null

  return (
    <div className="fixed inset-y-0 right-0 w-full sm:w-96 bg-white border-l border-gray-200 shadow-lg z-50 flex flex-col">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
        <h3 className="text-sm font-semibold text-gray-900 truncate">{nodeId}</h3>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-700 text-lg">&times;</button>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {loading && (
          <div className="animate-pulse space-y-3">
            <div className="h-4 w-1/2 bg-gray-200 rounded" />
            <div className="h-3 w-full bg-gray-100 rounded" />
            <div className="h-3 w-5/6 bg-gray-100 rounded" />
            <div className="h-3 w-3/4 bg-gray-100 rounded" />
          </div>
        )}

        {error && (
          <div className="text-sm text-gray-600 bg-gray-50 rounded p-3">
            <p className="font-medium text-gray-700 mb-1">Pasal tidak ditemukan di database</p>
            <p className="text-xs text-gray-500">Kemungkinan pasal ini belum di-ingest ke graph, atau LLM mengutip referensi yang tidak tepat.</p>
            <p className="text-xs text-blue-600 mt-2 font-mono">{nodeId}</p>
          </div>
        )}

        {data && (
          <div className="space-y-4">
            <div>
              <span className="text-xs text-gray-500 uppercase">{data.type} {data.number}</span>
            </div>

            {data.text && (
              <div className="text-sm text-gray-700 whitespace-pre-line leading-relaxed">
                {data.text}
              </div>
            )}

            {data.children.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">Isi</h4>
                <ul className="space-y-1">
                  {data.children.map(c => (
                    <li key={c.node_id} className="text-xs text-gray-600 border-l-2 border-gray-200 pl-2">
                      <span className="font-medium">{c.type} {c.number}</span>
                      {c.text_preview && <span className="ml-1 text-gray-400">— {c.text_preview}</span>}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {data.norms_derived.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">Norma Turunan</h4>
                <ul className="space-y-1">
                  {data.norms_derived.map(n => (
                    <li key={n.id} className="text-xs text-gray-600">
                      <span className="inline-block rounded bg-blue-100 text-blue-700 px-1 mr-1">{n.severity}</span>
                      {n.description}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
