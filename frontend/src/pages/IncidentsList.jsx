import { useState } from 'react'
import { useIncidents } from '../hooks/useIncidents'
import useIncidentStore from '../store/incidentStore'
import IncidentCard from '../components/incidents/IncidentCard'
import LoadingSpinner from '../components/shared/LoadingSpinner'
import EmptyState from '../components/shared/EmptyState'
import ErrorBoundary from '../components/shared/ErrorBoundary'

const SEVERITY_FILTERS = ['all', 'critical', 'high', 'medium', 'low']

function mergeAndDedupe(polled, live) {
  const byId = new Map()
  polled.forEach((i) => byId.set(i.id, i))
  live.forEach((i) => byId.set(i.id, { ...i, ...byId.get(i.id) }))
  return [...byId.values()].sort((a, b) => {
    const ta = new Date(a.occurred_at || a.created_at || 0).getTime()
    const tb = new Date(b.occurred_at || b.created_at || 0).getTime()
    return tb - ta
  })
}

export default function IncidentsList() {
  const [severityFilter, setSeverityFilter] = useState('all')
  const { data, isLoading, error } = useIncidents({})
  const { liveIncidents } = useIncidentStore()
  const list = data?.results ?? (Array.isArray(data) ? data : [])
  const merged = mergeAndDedupe(list, liveIncidents)
  const filtered =
    severityFilter === 'all'
      ? merged
      : merged.filter((i) => (i.severity || '').toLowerCase() === severityFilter)

  if (error) {
    return (
      <div className="p-6">
        <p className="text-accent-red">Failed to load incidents.</p>
      </div>
    )
  }

  return (
    <ErrorBoundary>
      <div className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h1 className="font-mono text-xl text-white">Incidents</h1>
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="rounded border border-border bg-surface2 px-3 py-1.5 text-sm font-mono text-white"
          >
            {SEVERITY_FILTERS.map((s) => (
              <option key={s} value={s}>
                {s === 'all' ? 'All' : s.charAt(0).toUpperCase() + s.slice(1)}
              </option>
            ))}
          </select>
        </div>
        {isLoading && !list.length ? (
          <div className="flex justify-center py-12">
            <LoadingSpinner />
          </div>
        ) : !filtered.length ? (
          <EmptyState title="No incidents" description="Incidents will appear here when they occur." />
        ) : (
          <ul className="space-y-2">
            {filtered.map((incident) => (
              <li key={incident.id}>
                <IncidentCard incident={incident} />
              </li>
            ))}
          </ul>
        )}
      </div>
    </ErrorBoundary>
  )
}
