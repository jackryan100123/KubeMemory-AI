import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { usePatterns } from '../hooks/usePatterns'
import { useIncidents } from '../hooks/useIncidents'
import { fetchMemoryPatterns } from '../api/memory'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  BarChart,
  Bar,
  Legend,
} from 'recharts'
import { format, subDays } from 'date-fns'
import LoadingSpinner from '../components/shared/LoadingSpinner'
import SkeletonLoader from '../components/shared/SkeletonLoader'
import ErrorBoundary from '../components/shared/ErrorBoundary'

const INCIDENT_TYPE_COLORS = {
  CrashLoopBackOff: '#f7604f',
  OOMKill: '#f97316',
  ImagePullBackOff: '#f7c94f',
  NodePressure: '#4f8ef7',
  Evicted: '#9b59b6',
  Pending: '#6b7a99',
  Unknown: '#6b7a99',
}

export default function Patterns() {
  const [sortBy, setSortBy] = useState('frequency')
  const [sortOrder, setSortOrder] = useState('desc')
  const { data: patternsData, isLoading: patternsLoading } = usePatterns()
  const { data: incidentsData } = useIncidents({
    occurred_after: subDays(new Date(), 30).toISOString(),
  })
  const { data: memoryPatternsData, isLoading: memoryPatternsLoading } = useQuery({
    queryKey: ['memoryPatterns'],
    queryFn: fetchMemoryPatterns,
    staleTime: 60000,
  })

  const patterns = patternsData?.results ?? (Array.isArray(patternsData) ? patternsData : [])
  const incidents = incidentsData?.results ?? (Array.isArray(incidentsData) ? incidentsData : [])
  const deployPatterns = memoryPatternsData?.patterns ?? []

  const chart1Data = useMemo(() => {
    const byDay = {}
    for (let d = 29; d >= 0; d--) {
      const day = format(subDays(new Date(), d), 'yyyy-MM-dd')
      byDay[day] = {
        date: format(subDays(new Date(), d), 'MMM d'),
        key: day,
        ...Object.fromEntries(
          Object.keys(INCIDENT_TYPE_COLORS).map((t) => [t, 0])
        ),
      }
    }
    incidents.forEach((i) => {
      const day = (i.occurred_at || '').slice(0, 10)
      if (!byDay[day]) return
      const t = i.incident_type || 'Unknown'
      if (t in byDay[day]) byDay[day][t]++
    })
    return Object.entries(byDay).map(([, v]) => v)
  }, [incidents])

  const chart2Data = useMemo(
    () =>
      deployPatterns.slice(0, 15).map((p) => ({
        service: p.service || 'unknown',
        crashes: p.crash_count ?? 0,
      })),
    [deployPatterns]
  )

  const chart3Data = useMemo(
    () =>
      patterns.slice(0, 12).map((p) => ({
        name: `${p.pod_name} / ${p.incident_type}`,
        rate: Math.round((p.fix_success_rate ?? 0) * 100),
      })),
    [patterns]
  )

  const sortedPatterns = useMemo(() => {
    const list = [...patterns]
    const key = sortBy === 'last_seen' ? 'last_seen' : sortBy
    list.sort((a, b) => {
      let va = a[key]
      let vb = b[key]
      if (key === 'last_seen') {
        va = new Date(va || 0).getTime()
        vb = new Date(vb || 0).getTime()
      }
      if (sortOrder === 'desc') return (vb ?? 0) - (va ?? 0)
      return (va ?? 0) - (vb ?? 0)
    })
    return list
  }, [patterns, sortBy, sortOrder])

  const toggleSort = (key) => {
    if (sortBy === key) setSortOrder((o) => (o === 'desc' ? 'asc' : 'desc'))
    else setSortBy(key)
  }

  return (
    <ErrorBoundary>
      <div className="p-6 space-y-6">
        {/* Chart 1 — Incident frequency over time */}
        <div className="rounded-lg border border-border bg-surface p-4">
          <h3 className="font-mono font-semibold text-white mb-4">
            Incident Frequency Over Time (30 days)
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chart1Data} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e2433" />
                <XAxis dataKey="date" tick={{ fill: '#6b7a99', fontSize: 10 }} />
                <YAxis tick={{ fill: '#6b7a99', fontSize: 10 }} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#111318', border: '1px solid #1e2433' }}
                />
                <Legend />
                {Object.entries(INCIDENT_TYPE_COLORS).map(([type, color]) => (
                  <Area
                    key={type}
                    type="monotone"
                    dataKey={type}
                    stackId="1"
                    stroke={color}
                    fill={color}
                    fillOpacity={0.6}
                    name={type}
                  />
                ))}
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Chart 2 — Deploy-to-crash */}
          <div className="rounded-lg border border-border bg-surface p-4">
            <h3 className="font-mono font-semibold text-white mb-4">
              Deploy-to-Crash Correlation
            </h3>
            {memoryPatternsLoading ? (
              <SkeletonLoader lines={5} />
            ) : (
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={chart2Data}
                    layout="vertical"
                    margin={{ top: 5, right: 5, left: 80, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e2433" />
                    <XAxis type="number" tick={{ fill: '#6b7a99', fontSize: 10 }} />
                    <YAxis
                      type="category"
                      dataKey="service"
                      tick={{ fill: '#6b7a99', fontSize: 10 }}
                      width={75}
                    />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#111318', border: '1px solid #1e2433' }}
                    />
                    <Bar dataKey="crashes" fill="#00d4aa" name="Crashes after deploy" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          {/* Chart 3 — Fix success rate */}
          <div className="rounded-lg border border-border bg-surface p-4">
            <h3 className="font-mono font-semibold text-white mb-4">
              Fix Success Rate (by pattern)
            </h3>
            {patternsLoading ? (
              <SkeletonLoader lines={5} />
            ) : (
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={chart3Data}
                    layout="vertical"
                    margin={{ top: 5, right: 5, left: 120, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e2433" />
                    <XAxis
                      type="number"
                      domain={[0, 100]}
                      tick={{ fill: '#6b7a99', fontSize: 10 }}
                    />
                    <YAxis
                      type="category"
                      dataKey="name"
                      tick={{ fill: '#6b7a99', fontSize: 9 }}
                      width={115}
                    />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#111318', border: '1px solid #1e2433' }}
                      formatter={(v) => [`${v}%`, 'Fix rate']}
                    />
                    <Bar dataKey="rate" name="Fix rate %" fill="#4f8ef7" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </div>

        {/* Pattern table */}
        <div className="rounded-lg border border-border bg-surface overflow-hidden">
          <div className="px-4 py-3 border-b border-border font-mono font-semibold text-white">
            Cluster Patterns
          </div>
          {patternsLoading ? (
            <div className="p-4">
              <SkeletonLoader lines={8} />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm font-mono">
                <thead>
                  <tr className="text-muted text-left border-b border-border">
                    <th
                      className="px-4 py-3 cursor-pointer hover:text-white"
                      onClick={() => toggleSort('pod_name')}
                    >
                      Pod {sortBy === 'pod_name' && (sortOrder === 'desc' ? ' ↓' : ' ↑')}
                    </th>
                    <th className="px-4 py-3">Namespace</th>
                    <th className="px-4 py-3">Incident Type</th>
                    <th
                      className="px-4 py-3 cursor-pointer hover:text-white"
                      onClick={() => toggleSort('frequency')}
                    >
                      Frequency {sortBy === 'frequency' && (sortOrder === 'desc' ? ' ↓' : ' ↑')}
                    </th>
                    <th className="px-4 py-3">Best Fix</th>
                    <th className="px-4 py-3">Success Rate</th>
                    <th
                      className="px-4 py-3 cursor-pointer hover:text-white"
                      onClick={() => toggleSort('last_seen')}
                    >
                      Last Seen {sortBy === 'last_seen' && (sortOrder === 'desc' ? ' ↓' : ' ↑')}
                    </th>
                  </tr>
                </thead>
                <tbody className="text-white">
                  {sortedPatterns.map((p) => (
                    <tr key={`${p.pod_name}-${p.namespace}-${p.incident_type}`} className="border-b border-border hover:bg-surface2">
                      <td className="px-4 py-2">{p.pod_name}</td>
                      <td className="px-4 py-2">{p.namespace}</td>
                      <td className="px-4 py-2">{p.incident_type}</td>
                      <td className="px-4 py-2">{p.frequency}</td>
                      <td className="px-4 py-2 max-w-xs truncate" title={p.best_fix}>
                        {p.best_fix || '—'}
                      </td>
                      <td className="px-4 py-2">{Math.round((p.fix_success_rate ?? 0) * 100)}%</td>
                      <td className="px-4 py-2">
                        {p.last_seen ? format(new Date(p.last_seen), 'MMM d, HH:mm') : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {!patternsLoading && !sortedPatterns.length && (
            <p className="p-4 text-muted text-sm">No patterns yet.</p>
          )}
        </div>
      </div>
    </ErrorBoundary>
  )
}
