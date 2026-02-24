import { clsx } from 'clsx'

const severityStyles = {
  critical: 'bg-accent-red/20 text-accent-red border-accent-red/50',
  high: 'bg-orange-500/20 text-orange-400 border-orange-500/50',
  medium: 'bg-accent-yellow/20 text-accent-yellow border-accent-yellow/50',
  low: 'bg-muted/30 text-muted border-border',
}

export default function SeverityBadge({ severity }) {
  const s = (severity || 'low').toLowerCase()
  const style = severityStyles[s] ?? severityStyles.low
  const label = s.charAt(0).toUpperCase() + s.slice(1)
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded border px-2 py-0.5 text-xs font-mono font-semibold',
        style
      )}
    >
      {label}
    </span>
  )
}
