interface Props {
  severity: 'critical' | 'high' | 'medium' | 'low'
}

const COLORS: Record<string, string> = {
  critical: 'bg-red-100 text-red-800',
  high: 'bg-orange-100 text-orange-800',
  medium: 'bg-yellow-100 text-yellow-800',
  low: 'bg-blue-100 text-blue-800',
}

export default function SeverityBadge({ severity }: Props) {
  return (
    <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase shrink-0 ${COLORS[severity] || COLORS.medium}`}>
      {severity}
    </span>
  )
}
