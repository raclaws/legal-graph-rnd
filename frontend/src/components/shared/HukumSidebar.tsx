import { useEffect, useRef } from 'react'
import type { HukumItem } from '../../types'
import SeverityBadge from './SeverityBadge'

interface Props {
  items: HukumItem[]
  focusedIndex: number | null
  onCitationClick?: (nodeId: string) => void
}

function formatPasal(nodeId: string): string {
  const m = nodeId.match(/^(\w+)\/(\d+)\/(\d+)\/.*?Pasal\/(\d+\w*)/)
  if (m) return `${m[1]} ${m[3]}/${m[2]} Pasal ${m[4]}`
  return nodeId
}

export default function HukumSidebar({ items, focusedIndex, onCitationClick }: Props) {
  const refs = useRef<(HTMLLIElement | null)[]>([])

  useEffect(() => {
    if (focusedIndex !== null && refs.current[focusedIndex]) {
      refs.current[focusedIndex]?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }, [focusedIndex])

  if (items.length === 0) return null

  return (
    <aside className="fixed top-[57px] right-0 w-80 h-[calc(100vh-57px)] border-l border-gray-200 bg-white overflow-y-auto z-40">
      <div className="px-4 py-3 border-b border-gray-100 sticky top-0 bg-white">
        <h3 className="text-xs font-semibold text-blue-700 uppercase tracking-wide">Hukum</h3>
        <p className="text-[10px] text-gray-400 mt-0.5">{items.length} ketentuan ditemukan</p>
      </div>
      <ul className="divide-y divide-gray-50">
        {items.map((item, i) => (
          <li
            key={i}
            ref={el => { refs.current[i] = el }}
            className={`px-4 py-3 transition-colors ${focusedIndex === i ? 'bg-blue-50 ring-1 ring-blue-200' : 'hover:bg-gray-50'}`}
          >
            <div className="flex items-start gap-2">
              <SeverityBadge severity={item.severity} />
              <p className="text-xs text-gray-700 leading-relaxed">{item.description}</p>
            </div>
            {item.doc_evidence && (
              <p className="mt-1 ml-7 text-[10px] text-gray-500 bg-gray-100 rounded px-2 py-1 italic">
                📄 {item.doc_evidence}
              </p>
            )}
            {item.legal_basis && (
              <button
                onClick={() => onCitationClick?.(item.legal_basis)}
                className="mt-1 text-[10px] text-blue-600 hover:underline ml-7"
              >
                {formatPasal(item.legal_basis)}
              </button>
            )}
          </li>
        ))}
      </ul>
    </aside>
  )
}
