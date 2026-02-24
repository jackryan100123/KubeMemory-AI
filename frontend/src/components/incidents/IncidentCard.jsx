import { useNavigate } from 'react-router-dom'
import { formatDistanceToNow } from 'date-fns'
import SeverityBadge from './SeverityBadge'
import clsx from 'clsx'

const severityBorder = {
  critical: 'border-l-accent-red',
  high: 'border-l-orange-500',
  medium: 'border-l-accent-yellow',
  low: 'border-l-muted',
}

export default function IncidentCard({ incident, onClick }) {
  const navigate = useNavigate()
  const severity = (incident.severity || 'low').toLowerCase()
  const borderClass = severityBorder[severity] ?? severityBorder.low
  const occurredAt = incident.occurred_at ? new Date(incident.occurred_at) : null
  const timeAgo = occurredAt ? formatDistanceToNow(occurredAt, { addSuffix: true }) : '—'
  const hasAnalysis = !!incident.ai_analysis?.trim()
  const analysisStatus = hasAnalysis ? 'AI analysis ready' : 'Analyzing...'

  const handleClick = () => {
    if (onClick) onClick(incident)
    else navigate(`/incidents/${incident.id}`)
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      className={clsx(
        'w-full text-left rounded-r border border-border border-l-4 bg-surface hover:bg-surface2 transition-colors p-3 animate-slide-in',
        borderClass
      )}
    >
      <div className="flex items-center gap-2 flex-wrap">
        <SeverityBadge severity={incident.severity} />
        <span className="font-mono text-sm text-white">
          {incident.incident_type} — {incident.pod_name}
        </span>
        <span className="text-muted text-xs font-mono ml-auto shrink-0">{timeAgo}</span>
      </div>
      <div className="mt-1 text-xs text-muted">
        {incident.namespace} • {incident.node_name || '—'} • {analysisStatus}
      </div>
    </button>
  )
}
