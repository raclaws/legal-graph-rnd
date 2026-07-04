import { useState, useEffect, useRef, useMemo } from 'react'
import type { HukumItem } from '../../types'

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
  if (!m) return ''
  return m[2] ? `Ps.${m[1]}(${m[2]})` : `Ps.${m[1]}`
}

function severityPillClass(severity: string): string {
  switch (severity) {
    case 'critical': return 'bg-red-100 text-red-800'
    case 'high': return 'bg-orange-100 text-orange-800'
    case 'medium': return 'bg-yellow-100 text-yellow-800'
    default: return 'bg-blue-100 text-blue-700'
  }
}

interface GroupedReg {
  regKey: string
  items: { item: HukumItem; originalIndex: number }[]
}

function SidebarContent({ grouped, collapsed, toggleGroup, focusedIndex, onCitationClick, refs }: {
  grouped: GroupedReg[]
  collapsed: Set<string>
  toggleGroup: (key: string) => void
  focusedIndex: number | null
  onCitationClick?: (nodeId: string) => void
  refs: React.MutableRefObject<(HTMLLIElement | null)[]>
}) {
  return (
    <div className="divide-y divide-gray-100">
      {grouped.map((group, gi) => (
        <div key={gi}>
          {group.regKey && (
            <button
              onClick={() => toggleGroup(group.regKey)}
              className="w-full px-4 pt-3 pb-1 flex items-center gap-1.5 hover:bg-gray-50 text-left"
            >
              <span className="text-[10px] text-gray-400">{collapsed.has(group.regKey) ? '▶' : '▼'}</span>
              <span className="text-[10px] font-semibold text-gray-500 uppercase">{group.regKey}</span>
              <span className="text-[10px] text-gray-400">({group.items.length})</span>
            </button>
          )}
          {!collapsed.has(group.regKey) && (
            <ul>
              {group.items.map(({ item, originalIndex }) => (
                <li
                  key={originalIndex}
                  ref={el => { refs.current[originalIndex] = el }}
                  className={`px-4 py-2 transition-colors ${group.regKey ? 'pl-6' : ''} ${focusedIndex === originalIndex ? 'bg-blue-50 ring-1 ring-blue-200' : 'hover:bg-gray-50'}`}
                >
                  <div className="flex items-start gap-2">
                    {item.legal_basis ? (
                      <button
                        onClick={() => onCitationClick?.(item.legal_basis)}
                        className={`shrink-0 mt-0.5 rounded px-1.5 py-0.5 text-[10px] font-medium hover:opacity-80 transition-opacity ${severityPillClass(item.severity)}`}
                      >
                        {formatPasalShort(item.legal_basis)}
                      </button>
                    ) : (
                      <span className={`shrink-0 mt-0.5 rounded px-1.5 py-0.5 text-[10px] font-medium ${severityPillClass(item.severity)}`}>
                        {item.severity}
                      </span>
                    )}
                    <p className="text-xs text-gray-700 leading-relaxed">{item.description}</p>
                  </div>
                  {item.doc_evidence && (
                    <p className="mt-1 ml-7 text-[10px] text-gray-500 bg-gray-100 rounded px-2 py-1 italic">
                      {item.doc_evidence}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </div>
  )
}

export default function HukumSidebar({ items, focusedIndex, onCitationClick }: Props) {
  const refs = useRef<(HTMLLIElement | null)[]>([])
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set())
  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => {
    if (focusedIndex !== null && refs.current[focusedIndex]) {
      refs.current[focusedIndex]?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      const item = items[focusedIndex]
      if (item?.legal_basis) {
        const key = getRegKey(item.legal_basis)
        if (collapsed.has(key)) {
          setCollapsed(prev => { const n = new Set(prev); n.delete(key); return n })
        }
      }
    }
  }, [focusedIndex])

  // Open mobile sheet on citation focus
  useEffect(() => {
    if (focusedIndex !== null && items.length > 0) {
      setMobileOpen(true)
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

  function toggleGroup(key: string) {
    setCollapsed(prev => {
      const n = new Set(prev)
      if (n.has(key)) n.delete(key)
      else n.add(key)
      return n
    })
  }

  if (items.length === 0) return null

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden md:block fixed top-[57px] right-0 w-80 h-[calc(100vh-57px)] border-l border-gray-200 bg-white overflow-y-auto z-40">
        <div className="px-4 py-3 border-b border-gray-100 sticky top-0 bg-white">
          <h3 className="text-xs font-semibold text-blue-700 uppercase tracking-wide">Hukum</h3>
          <p className="text-[10px] text-gray-400 mt-0.5">{items.length} ketentuan ditemukan</p>
        </div>
        <SidebarContent grouped={grouped} collapsed={collapsed} toggleGroup={toggleGroup} focusedIndex={focusedIndex} onCitationClick={onCitationClick} refs={refs} />
      </aside>

      {/* Mobile floating button */}
      <button
        onClick={() => setMobileOpen(true)}
        className="md:hidden fixed bottom-20 right-4 z-40 bg-blue-600 text-white rounded-full w-10 h-10 flex items-center justify-center shadow-lg active:scale-95 transition-transform"
      >
        <span className="text-xs font-bold">{items.length}</span>
      </button>

      {/* Mobile bottom sheet */}
      {mobileOpen && (
        <div className="md:hidden fixed inset-0 z-50 flex flex-col justify-end">
          <div className="absolute inset-0 bg-black/30" onClick={() => setMobileOpen(false)} />
          <div className="relative bg-white rounded-t-2xl max-h-[70vh] flex flex-col animate-[slideUp_0.2s_ease-out]">
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
              <div>
                <h3 className="text-xs font-semibold text-blue-700 uppercase tracking-wide">Hukum</h3>
                <p className="text-[10px] text-gray-400">{items.length} ketentuan</p>
              </div>
              <button onClick={() => setMobileOpen(false)} className="text-gray-400 hover:text-gray-700 text-lg px-2">&times;</button>
            </div>
            <div className="overflow-y-auto flex-1 pb-safe">
              <SidebarContent grouped={grouped} collapsed={collapsed} toggleGroup={toggleGroup} focusedIndex={focusedIndex} onCitationClick={(nodeId) => { setMobileOpen(false); onCitationClick?.(nodeId) }} refs={refs} />
            </div>
          </div>
        </div>
      )}
    </>
  )
}
