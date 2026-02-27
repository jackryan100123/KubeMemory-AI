import React from 'react'
import { useNavigate } from 'react-router-dom'

/**
 * Right panel (collapsible): Tools Used, Sources (incident IDs -> link to /incidents/:id), Active Cluster.
 */
export default function ContextPanel({
  toolsUsed = [],
  sourceIncidentIds = [],
  namespace = 'all',
  clusterName = '',
  wsConnected = false,
  collapsed,
  onToggleCollapsed,
}) {
  const navigate = useNavigate()

  if (collapsed) {
    return (
      <div className="w-10 shrink-0 border-l border-border flex flex-col items-center py-4">
        <button
          type="button"
          onClick={onToggleCollapsed}
          className="text-muted hover:text-white font-mono text-xs"
          title="Open context"
        >
          →
        </button>
      </div>
    )
  }

  return (
    <div className="w-72 shrink-0 border-l border-border bg-surface/50 flex flex-col overflow-hidden">
      <div className="p-3 border-b border-border flex items-center justify-between">
        <span className="font-mono text-sm text-white">Context</span>
        <button
          type="button"
          onClick={onToggleCollapsed}
          className="text-muted hover:text-white text-xs"
          title="Collapse"
        >
          ←
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-4">
        {toolsUsed.length > 0 && (
          <section>
            <h3 className="font-mono text-xs text-muted uppercase tracking-wider mb-2">
              Tools Used
            </h3>
            <div className="flex flex-wrap gap-1.5">
              {toolsUsed.map((t) => (
                <span
                  key={t}
                  className="px-2 py-1 rounded bg-surface2 border border-border text-xs font-mono text-white"
                >
                  {t}
                </span>
              ))}
            </div>
          </section>
        )}
        {sourceIncidentIds.length > 0 && (
          <section>
            <h3 className="font-mono text-xs text-muted uppercase tracking-wider mb-2">
              Sources
            </h3>
            <ul className="space-y-1">
              {sourceIncidentIds.map((id) => (
                <li key={id}>
                  <button
                    type="button"
                    onClick={() => navigate(`/incidents/${id}`)}
                    className="font-mono text-xs text-accent hover:underline"
                  >
                    Incident #{id}
                  </button>
                </li>
              ))}
            </ul>
          </section>
        )}
        <section>
          <h3 className="font-mono text-xs text-muted uppercase tracking-wider mb-2">
            Active Cluster
          </h3>
          <div className="font-mono text-xs text-white space-y-1">
            <p>Namespace: {namespace}</p>
            {clusterName && <p>{clusterName}</p>}
            <p className="flex items-center gap-1.5">
              <span
                className={`w-2 h-2 rounded-full ${
                  wsConnected ? 'bg-accent' : 'bg-muted'
                }`}
              />
              {wsConnected ? 'Connected' : 'Disconnected'}
            </p>
          </div>
        </section>
      </div>
    </div>
  )
}
