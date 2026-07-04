import { useState, useEffect } from 'react'

export default function ThreeSpaceSkeleton() {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    const t = setInterval(() => setElapsed(s => s + 1), 1000)
    return () => clearInterval(t)
  }, [])

  const label = elapsed < 3 ? 'Memproses...' : elapsed < 8 ? 'Mencari regulasi...' : 'Menganalisis...'

  return (
    <div className="flex items-center gap-3 py-3">
      <div className="flex gap-1">
        <span className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce [animation-delay:0ms]" />
        <span className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce [animation-delay:150ms]" />
        <span className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce [animation-delay:300ms]" />
      </div>
      <span className="text-sm text-gray-500">{label}</span>
      <span className="text-xs text-gray-400 tabular-nums">{elapsed}s</span>
    </div>
  )
}
