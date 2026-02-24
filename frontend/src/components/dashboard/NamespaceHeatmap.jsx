/**
 * Namespace health score from open incidents.
 * score = 100 - (critical*25) - (high*10) - (medium*3), min 0.
 */
export function namespaceHealth(namespace, incidents) {
  const list = Array.isArray(incidents) ? incidents : (incidents?.results || [])
  const nsIncidents = list.filter((i) => (i.namespace || '') === namespace && (i.status || '') !== 'resolved')
  const critical = nsIncidents.filter((i) => (i.severity || '').toLowerCase() === 'critical').length
  const high = nsIncidents.filter((i) => (i.severity || '').toLowerCase() === 'high').length
  const medium = nsIncidents.filter((i) => (i.severity || '').toLowerCase() === 'medium').length
  return Math.max(0, 100 - critical * 25 - high * 10 - medium * 3)
}

export default function NamespaceHeatmap({ incidents, namespaces, onSelectNamespace, selectedNamespace }) {
  const list = Array.isArray(incidents) ? incidents : (incidents?.results || [])
  const nsList = namespaces && namespaces.length > 0
    ? namespaces
    : [...new Set(list.map((i) => i.namespace).filter(Boolean))]

  return (
    <div className="rounded-lg border border-border bg-surface overflow-hidden">
      <div className="px-4 py-3 border-b border-border">
        <span className="font-mono font-semibold text-white">NAMESPACE HEALTH</span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 p-4">
        {nsList.map((ns) => {
          const score = namespaceHealth(ns, list)
          const nsIncidents = list.filter((i) => i.namespace === ns && i.status !== 'resolved')
          const criticalCount = nsIncidents.filter((i) => (i.severity || '').toLowerCase() === 'critical').length
          const isGreen = score > 80
          const isYellow = score >= 50 && score <= 80
          const isRed = score < 50
          const barColor = isGreen ? 'bg-accent' : isYellow ? 'bg-yellow-500' : 'bg-accent-red'
          return (
            <button
              type="button"
              key={ns}
              onClick={() => onSelectNamespace?.(selectedNamespace === ns ? null : ns)}
              className={`text-left p-3 rounded-lg border transition-colors ${
                selectedNamespace === ns ? 'border-accent bg-accent/10' : 'border-border bg-surface2 hover:bg-surface'
              }`}
            >
              <p className="font-mono text-sm text-white truncate">{ns}</p>
              <div className="flex items-center gap-2 mt-2">
                <div className="flex-1 h-2 rounded bg-surface overflow-hidden">
                  <div
                    className={`h-full rounded ${barColor}`}
                    style={{ width: `${Math.min(100, score)}%` }}
                  />
                </div>
                <span className="text-xs font-mono text-muted">{Math.round(score)}%</span>
              </div>
              <p className="text-xs text-muted mt-1">
                {nsIncidents.length} incident{nsIncidents.length !== 1 ? 's' : ''}
                {criticalCount > 0 ? ` • ${criticalCount} critical` : ' • ✓ healthy'}
              </p>
            </button>
          )
        })}
      </div>
    </div>
  )
}
