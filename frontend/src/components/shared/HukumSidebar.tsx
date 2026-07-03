import { useEffect, useRef, useMemo } from 'react'
import type { HukumItem } from '../../types'
import SeverityBadge from './SeverityBadge'

interface Props {
  items: HukumItem[]
  focusedIndex: number | null
  onCitationClick?: (nodeId: string) => void
}

function getRegKey(nodeId: string): string {
  const m = nodeId.match(/^(\w+)\/(\d+)\/(\d+)/)
  return m ? `${m[1]} ${m[3]}/${m[2]}` : ''
}

function formatPasalShort(nodeId: string): string {
  const m = nodeId.match(/Pasal\/(\d+\w*)(?:\/Ayat\/(\d+))?/)
  if (!m) return nodeId
  return m[2] ? `Ps. ${m[1]} Ayat ${m[2]}` : `Ps. ${m[1]}`
}

interface GroupedReg {
  regKey: string
  items: { item: HukumItem; originalIndex: number }[]
}

export default function HukumSidebar({ items, focusedIndex, onCitationClick }: Props) {
  const refs = useRef<(HTMLLIElement | null)[]>([])

  useEffect(() => {
    if (focusedIndex !== null && refs.current[focusedIndex]) {
      refs.current[focusedIndex]?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }, [focusedIndex])

  const grouped = useMemo(() => {
    const groups: GroupedReg[] = []
    const map = new Map<string, GroupedReg>()

    items.forEach((item, i) => {
      const key = item.legal_basis ? getRegKey(item.legal_basis) : ''
      if (key && map.has(key)) {
        map.get(key)!.items.push({ item, originalIndex: i })
      } else if (key) {
        const g: GroupedReg = { regKey: key, items: [{ item, originalIndex: i }] }
        map.set(key, g)
        groups.push(g)
      } else {
        groups.push({ regKey: '', items: [{ item, originalIndex: i }] })
      }
    })

    return groups
  }, [items])

  if (items.length === 0) return null

  return (
    <aside className="fixed top-[57px] right-0 w-80 h-[calc(100vh-57px)] border-l border-gray-200 bg-white overflow-y-auto z-40">
      <div className="px-4 py-3 border-b border-gray-100 sticky top-0 bg-white">
        <h3 className="text-xs font-semibold text-blue-700 uppercase tracking-wide">Hukum</h3>
        <p className="text-[10px] text-gray-400 mt-0.5">{items.length} ketentuan ditemukan</p>
      </div>
      <div className="divide-y divide-gray-100">
        {grouped.map((group, gi) => (
          <div key={gi}>
            {group.regKey && (
              <div className="px-4 pt-3 pb-1">
                <span className="text-[10px] font-semibold text-gray-500 uppercase">{group.regKey}</span>
              </div>
            )}
            <ul>
              {group.items.map(({ item, originalIndex }) => (
                <li
                  key={originalIndex}
                  ref={el => { refs.current[originalIndex] = el }}
                  className={`px-4 py-2 transition-colors ${group.regKey ? 'pl-6' : ''} ${focusedIndex === originalIndex ? 'bg-blue-50 ring-1 ring-blue-200' : 'hover:bg-gray-50'}`}
                >
                  <div className="flex items-start gap-2">
                    <SeverityBadge severity={item.severity} />
                    <p className="text-xs text-gray-700 leading-relaxed">{item.description}</p>
                  </div>
                  {item.doc_evidence && (
                    <p className="mt-1 ml-7 text-[10px] text-gray-500 bg-gray-100 rounded px-2 py-1 italic">
                      {item.doc_evidence}
                    </p>
                  )}
                  {item.legal_basis && (
                    <button
                      onClick={() => onCitationClick?.(item.legal_basis)}
                      className="mt-1 text-[10px] text-blue-600 hover:underline ml-7"
                    >
                      {formatPasalShort(item.legal_basis)}
                    </button>
                  )}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </aside>
  )
}
