import { useState, useMemo } from 'react'
import { useIncidents } from '../hooks/useIncidents'
import { usePatterns } from '../hooks/usePatterns'
import { useAgentStatus } from '../hooks/useAgentStatus'
import useIncidentStore from '../store/incidentStore'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts'
import { format, subDays } from 'date-fns'
import IncidentCard from '../components/incidents/IncidentCard'
import LoadingSpinner from '../components/shared/LoadingSpinner'
import SkeletonLoader from '../components/shared/SkeletonLoader'
import EmptyState from '../components/shared/EmptyState'
import ErrorBoundary from '../components/shared/ErrorBoundary'
import NamespaceHeatmap from '../components/dashboard/NamespaceHeatmap'

const SEVERITY_FILTERS = [
  { value: 'all', label: 'All' },
  { value: 'critical', label: 'Critical' },
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' },
]

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

function clusterHealth(incidents) {
  const list = incidents?.results ?? (Array.isArray(incidents) ? incidents : [])
  let score = 100
  for (const i of list) {
    const s = (i.severity || '').toLowerCase()
    if (s === 'critical') score -= 20
    else if (s === 'high') score -= 5
    else if (s === 'medium') score -= 2
  }
  return Math.max(0, Math.min(100, score))
}

export default function Dashboard() {
  const [feedFilter, setFeedFilter] = useState('all')
  const [heatmapNamespace, setHeatmapNamespace] = useState(null)
  const { data: openData } = useIncidents({ status: 'open' })
  const { data: allForStats } = useIncidents({})
  const { data: patternsData, isLoading: patternsLoading } = usePatterns()
  const { data: agentStatus } = useAgentStatus()
  const { data: weekData } = useIncidents({
    occurred_after: subDays(new Date(), 7).toISOString(),
  })
  const { liveIncidents } = useIncidentStore()

  const openList = openData?.results ?? (Array.isArray(openData) ? openData : [])
  const allList = allForStats?.results ?? (Array.isArray(allForStats) ? allForStats : [])
  const mergedFeed = mergeAndDedupe(allList, liveIncidents)
  const feedByNs = heatmapNamespace
    ? mergedFeed.filter((i) => (i.namespace || '') === heatmapNamespace)
    : mergedFeed
  const filteredFeed =
    feedFilter === 'all'
      ? feedByNs
      : feedByNs.filter((i) => (i.severity || '').toLowerCase() === feedFilter)

  const resolvedToday = useMemo(() => {
    const today = format(new Date(), 'yyyy-MM-dd')
    return (allList || []).filter(
      (i) => i.status === 'resolved' && i.resolved_at && i.resolved_at.startsWith(today)
    ).length
  }, [allList])

  const criticalCount = (openList || []).filter(
    (i) => (i.severity || '').toLowerCase() === 'critical'
  ).length
  const health = clusterHealth(allList)
  const patterns = patternsData?.results ?? (Array.isArray(patternsData) ? patternsData : [])
  const topPatterns = patterns.slice(0, 5)
  const agentOk = agentStatus?.ollama_ok && agentStatus?.chroma_doc_count !== undefined

  const wasteThisMonth = useMemo(() => {
    const monthStart = new Date(new Date().getFullYear(), new Date().getMonth(), 1)
    return (allList || []).filter((i) => new Date(i.occurred_at || 0) >= monthStart)
      .reduce((sum, i) => sum + (Number(i.estimated_waste_usd) || 0), 0)
  }, [allList])
  const wastePodCount = (allList || []).filter((i) => Number(i.estimated_waste_usd) > 0).length

  const chartData = useMemo(() => {
    const weekList = weekData?.results ?? (Array.isArray(weekData) ? weekData : [])
    const byDay = {}
    for (let d = 6; d >= 0; d--) {
      const day = format(subDays(new Date(), d), 'yyyy-MM-dd')
      byDay[day] = { date: format(subDays(new Date(), d), 'EEE'), critical: 0, high: 0, medium: 0, low: 0 }
    }
    weekList.forEach((i) => {
      const day = (i.occurred_at || '').slice(0, 10)
      if (!byDay[day]) return
      const s = (i.severity || 'low').toLowerCase()
      if (s in byDay[day]) byDay[day][s]++
    })
    return Object.entries(byDay).map(([k, v]) => ({ ...v, key: k }))
  }, [weekData])

  return (
    <ErrorBoundary>
      <div className="p-6 space-y-6">
        {/* Section 1 — Stats Row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-4">
          <div className="rounded-lg border border-border bg-surface p-4">
            <p className="text-muted text-xs font-mono uppercase tracking-wider">Open Incidents</p>
            <p className="text-2xl font-mono font-bold text-white mt-1">{openList?.length ?? 0}</p>
            <p className="text-accent text-xs font-mono mt-1">↑ vs 24h</p>
          </div>
          <div className="rounded-lg border border-border bg-surface p-4">
            <p className="text-muted text-xs font-mono uppercase tracking-wider">Critical Right Now</p>
            <p className="text-2xl font-mono font-bold text-accent-red mt-1">{criticalCount}</p>
            {criticalCount > 0 && <span className="text-accent-red text-lg">🔴</span>}
          </div>
          <div className="rounded-lg border border-border bg-surface p-4">
            <p className="text-muted text-xs font-mono uppercase tracking-wider">Resolved Today</p>
            <p className="text-2xl font-mono font-bold text-accent mt-1">{resolvedToday}</p>
            <p className="text-accent text-xs font-mono mt-1">✓</p>
          </div>
          <div className="rounded-lg border border-border bg-surface p-4">
            <p className="text-muted text-xs font-mono uppercase tracking-wider">Cluster Health</p>
            <p className="text-2xl font-mono font-bold text-white mt-1">{health}%</p>
            <div className="flex gap-0.5 mt-1">
              {[1, 2, 3, 4, 5].map((i) => (
                <div
                  key={i}
                  className={`h-1.5 flex-1 rounded ${
                    i * 20 <= health ? 'bg-accent' : 'bg-surface2'
                  }`}
                />
              ))}
            </div>
          </div>
          <div className="rounded-lg border border-border bg-surface p-4">
            <p className="text-muted text-xs font-mono uppercase tracking-wider">Estimated Waste This Month</p>
            <p className="text-2xl font-mono font-bold text-white mt-1">
              ${Math.round(wasteThisMonth).toLocaleString()}
            </p>
            <p className="text-muted text-xs font-mono mt-1">
              across {wastePodCount} pod{wastePodCount !== 1 ? 's' : ''} • fix these now
            </p>
          </div>
          <div className="rounded-lg border border-border bg-surface p-4">
            <p className="text-muted text-xs font-mono uppercase tracking-wider">AI Pipeline</p>
            <p className="text-2xl font-mono font-bold mt-1">
              {agentStatus === undefined ? (
                <span className="text-muted">…</span>
              ) : agentOk ? (
                <span className="text-accent">Ready</span>
              ) : (
                <span className="text-accent-red">Degraded</span>
              )}
            </p>
            <p className="text-muted text-xs font-mono mt-1">
              Ollama + ChromaDB
            </p>
          </div>
        </div>

        {/* Namespace Health Heatmap */}
        <NamespaceHeatmap
          incidents={allList}
          onSelectNamespace={setHeatmapNamespace}
          selectedNamespace={heatmapNamespace}
        />

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          {/* Section 2 — Live Incident Feed (60%) */}
          <div className="lg:col-span-3 rounded-lg border border-border bg-surface overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b border-border">
              <span className="font-mono font-semibold text-white flex items-center gap-2">
                <span className="text-accent-red">🔴</span> LIVE FEED
              </span>
              <select
                value={feedFilter}
                onChange={(e) => setFeedFilter(e.target.value)}
                className="rounded border border-border bg-surface2 px-2 py-1 text-sm font-mono text-white"
              >
                {SEVERITY_FILTERS.map((f) => (
                  <option key={f.value} value={f.value}>
                    {f.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="max-h-[400px] overflow-y-auto p-2 space-y-2">
              {!filteredFeed.length ? (
                <EmptyState
                  title="No incidents"
                  description="Incidents will appear here in real time."
                />
              ) : (
                filteredFeed.map((incident) => (
                  <IncidentCard key={incident.id} incident={incident} />
                ))
              )}
            </div>
          </div>

          {/* Section 3 — Top Recurring Patterns (40%) */}
          <div className="lg:col-span-2 rounded-lg border border-border bg-surface overflow-hidden">
            <div className="px-4 py-3 border-b border-border">
              <span className="font-mono font-semibold text-white">🔁 RECURRING PATTERNS</span>
            </div>
            <div className="p-4 space-y-4">
              {patternsLoading ? (
                <SkeletonLoader lines={5} />
              ) : !topPatterns.length ? (
                <EmptyState title="No patterns yet" description="Patterns appear after analysis." />
              ) : (
                topPatterns.map((p, idx) => (
                  <div
                    key={p.id != null ? `pattern-${p.id}` : `pattern-${p.pod_name}-${p.namespace}-${p.incident_type}-${idx}`}
                    className="border-b border-border pb-3 last:border-0 last:pb-0"
                  >
                    <p className="font-mono text-sm text-white">{p.pod_name}</p>
                    <p className="text-muted text-xs font-mono">
                      {p.incident_type} × {p.frequency}
                    </p>
                    <div className="flex items-center gap-2 mt-1">
                      <div className="flex-1 h-1.5 rounded bg-surface2 overflow-hidden">
                        <div
                          className="h-full bg-accent rounded"
                          style={{ width: `${(p.fix_success_rate || 0) * 100}%` }}
                        />
                      </div>
                      <span className="text-xs font-mono text-muted">
                        Fix rate: {Math.round((p.fix_success_rate || 0) * 100)}%
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Section 4 — Mini Activity Chart */}
        <div className="rounded-lg border border-border bg-surface p-4">
          <h3 className="font-mono font-semibold text-white mb-4">7-Day Incident Frequency</h3>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e2433" />
                <XAxis dataKey="date" tick={{ fill: '#6b7a99', fontSize: 11 }} />
                <YAxis tick={{ fill: '#6b7a99', fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#111318', border: '1px solid #1e2433' }}
                  labelStyle={{ color: '#00d4aa' }}
                />
                <Bar dataKey="critical" stackId="a" fill="#f7604f" name="Critical" />
                <Bar dataKey="high" stackId="a" fill="#f97316" name="High" />
                <Bar dataKey="medium" stackId="a" fill="#f7c94f" name="Medium" />
                <Bar dataKey="low" stackId="a" fill="#6b7a99" name="Low" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </ErrorBoundary>
  )
}
