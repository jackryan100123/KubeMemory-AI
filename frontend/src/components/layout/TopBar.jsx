import { useState } from 'react'
import { useIncidents } from '../../hooks/useIncidents'
import useIncidentStore from '../../store/incidentStore'
import clsx from 'clsx'

function namespacesFromIncidents(data) {
  const list = data?.results ?? (Array.isArray(data) ? data : [])
  const ns = [...new Set(list.map((i) => i.namespace).filter(Boolean))]
  return ns.length ? ns.sort() : ['default']
}

export default function TopBar() {
  const [nsOpen, setNsOpen] = useState(false)
  const { data: incidentsData } = useIncidents({})
  const { wsConnected, liveIncidents } = useIncidentStore()
  const namespaces = namespacesFromIncidents(incidentsData)
  const activeNamespace = typeof window !== 'undefined' && window.__KUBEMEMORY_NS__
    ? window.__KUBEMEMORY_NS__
    : namespaces[0] || 'default'

  const setNamespace = (ns) => {
    if (typeof window !== 'undefined') window.__KUBEMEMORY_NS__ = ns
    setNsOpen(false)
    window.dispatchEvent(new CustomEvent('kubememory:namespace', { detail: ns }))
  }

  const hasLiveActivity = liveIncidents.length > 0

  return (
    <header className="h-14 flex items-center justify-between px-4 border-b border-border bg-surface">
      <div className="flex items-center gap-4">
        <span className="font-mono font-bold text-lg text-white tracking-tight">
          KubeMemory
        </span>
        <div className="relative">
          <button
            type="button"
            onClick={() => setNsOpen(!nsOpen)}
            className="flex items-center gap-2 px-3 py-1.5 rounded bg-surface2 border border-border text-sm font-mono text-white hover:border-accent/50"
          >
            {activeNamespace}
            <span className="text-muted">▾</span>
          </button>
          {nsOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setNsOpen(false)} aria-hidden />
              <ul className="absolute top-full left-0 mt-1 py-1 rounded border border-border bg-surface2 shadow-lg z-20 min-w-[140px]">
                {namespaces.map((ns) => (
                  <li key={ns}>
                    <button
                      type="button"
                      onClick={() => setNamespace(ns)}
                      className={clsx(
                        'w-full text-left px-3 py-2 text-sm font-mono',
                        ns === activeNamespace ? 'text-accent bg-surface' : 'text-white hover:bg-surface'
                      )}
                    >
                      {ns}
                    </button>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      </div>
      <div className="flex items-center gap-3">
        <span
          className={clsx(
            'flex items-center gap-2 text-xs font-mono',
            wsConnected ? 'text-accent' : 'text-muted',
            hasLiveActivity && wsConnected && 'animate-pulse'
          )}
          title={wsConnected ? 'Live feed connected' : 'Connecting to live feed…'}
        >
          <span
            className={clsx(
              'inline-block h-2 w-2 rounded-full flex-shrink-0',
              wsConnected ? 'bg-accent' : 'bg-muted'
            )}
          />
          Live
        </span>
        <span
          className={clsx(
            'flex items-center gap-1.5 text-xs font-mono',
            wsConnected ? 'text-accent' : 'text-muted'
          )}
          title={wsConnected ? 'WebSocket connected' : 'WebSocket disconnected'}
        >
          <span
            className={clsx(
              'inline-block h-2 w-2 rounded-full',
              wsConnected ? 'bg-accent' : 'bg-muted'
            )}
          />
          {wsConnected ? 'WS' : 'WS'}
        </span>
      </div>
    </header>
  )
}
