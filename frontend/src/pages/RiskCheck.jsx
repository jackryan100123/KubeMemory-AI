import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchIncidents } from '../api/incidents'
import { fetchRiskCheck } from '../api/agents'

function useNamespacesAndServices() {
  const { data } = useQuery({
    queryKey: ['incidents', { list: 'all' }],
    queryFn: () => fetchIncidents({}).then((r) => r.results || []),
  })
  const list = Array.isArray(data) ? data : (data?.results || [])
  const namespaces = [...new Set(list.map((i) => i.namespace).filter(Boolean))]
  const byNs = {}
  list.forEach((i) => {
    if (!i.namespace || !i.service_name) return
    if (!byNs[i.namespace]) byNs[i.namespace] = new Set()
    byNs[i.namespace].add(i.service_name)
  })
  const servicesByNamespace = byNs
  return { namespaces: namespaces.sort(), servicesByNamespace, list }
}

export default function RiskCheck() {
  const { namespaces, servicesByNamespace } = useNamespacesAndServices()
  const [namespace, setNamespace] = useState('')
  const [service, setService] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  const services = namespace ? (servicesByNamespace[namespace] ? [...servicesByNamespace[namespace]] : []) : []

  const handleCheck = () => {
    if (!service || !namespace) return
    setLoading(true)
    setResult(null)
    fetchRiskCheck(service, namespace)
      .then(setResult)
      .catch((e) => setResult({ error: e.response?.data?.error || e.message }))
      .finally(() => setLoading(false))
  }

  const riskLevel = result?.risk_level
  const isHigh = riskLevel === 'high'
  const isMedium = riskLevel === 'medium'

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <div className="rounded-lg border border-border bg-surface p-6 space-y-6">
        <h1 className="text-xl font-mono font-bold text-white flex items-center gap-2">
          <span className="text-accent-red">⚠️</span> PRE-DEPLOY RISK CHECK
        </h1>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-mono text-muted mb-1">Service</label>
            <select
              value={service}
              onChange={(e) => setService(e.target.value)}
              className="w-full rounded border border-border bg-surface2 px-3 py-2 text-white font-mono"
            >
              <option value="">Select service</option>
              {services.sort().map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-mono text-muted mb-1">Namespace</label>
            <select
              value={namespace}
              onChange={(e) => { setNamespace(e.target.value); setService('') }}
              className="w-full rounded border border-border bg-surface2 px-3 py-2 text-white font-mono"
            >
              <option value="">Select namespace</option>
              {namespaces.map((ns) => (
                <option key={ns} value={ns}>{ns}</option>
              ))}
            </select>
          </div>
        </div>
        <button
          type="button"
          onClick={handleCheck}
          disabled={loading || !service || !namespace}
          className="px-4 py-2 rounded bg-accent text-bg font-mono font-semibold hover:opacity-90 disabled:opacity-50"
        >
          {loading ? 'Checking…' : 'CHECK RISK'}
        </button>

        {result?.error && (
          <div className="rounded border border-red-500/50 bg-red-500/10 p-4 text-sm text-red-400">
            {result.error}
          </div>
        )}

        {result && !result.error && (
          <div className={`rounded-lg border p-4 space-y-3 ${
            isHigh ? 'border-accent-red bg-accent-red/10' : isMedium ? 'border-yellow-500/50 bg-yellow-500/10' : 'border-accent/50 bg-accent/10'
          }`}>
            <p className={`font-mono font-bold ${
              isHigh ? 'text-accent-red' : isMedium ? 'text-yellow-400' : 'text-accent'
            }`}>
              {isHigh && '🔴 HIGH RISK — Not recommended to deploy now'}
              {isMedium && '🟡 MEDIUM RISK — Proceed with caution'}
              {riskLevel === 'low' && '🟢 LOW RISK — Safe to deploy'}
            </p>
            <p className="text-muted text-sm">{result.recommendation}</p>
            {result.open_incidents > 0 && (
              <p className="text-sm text-white">
                Open incidents for this service: {result.open_incidents}
              </p>
            )}
            {(result.blast_radius_unstable?.length > 0) && (
              <div>
                <p className="text-xs font-mono text-muted uppercase mb-1">Blast radius (unstable)</p>
                <ul className="list-disc list-inside text-sm text-white">
                  {result.blast_radius_unstable.map((b, i) => (
                    <li key={i}>{b.affected_pod} ({b.namespace}) — co-occurred {b.co_occurrence}x</li>
                  ))}
                </ul>
              </div>
            )}
            {(result.deploy_crash_history?.length > 0) && (
              <div>
                <p className="text-xs font-mono text-muted uppercase mb-1">Similar deploy risk patterns</p>
                <ul className="list-disc list-inside text-sm text-white">
                  {result.deploy_crash_history.map((d, i) => (
                    <li key={i}>
                      {d.service} — {d.crash_count} crash(es), avg ~{Math.round(d.avg_minutes_to_crash || 0)}m to crash
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {isHigh && (
              <div className="pt-2 border-t border-border">
                <p className="text-xs font-mono text-accent uppercase">✓ Safe to deploy when:</p>
                <ul className="text-sm text-muted mt-1 list-disc list-inside">
                  <li>All open incidents are resolved</li>
                  <li>No critical incidents in last 2 hours</li>
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
