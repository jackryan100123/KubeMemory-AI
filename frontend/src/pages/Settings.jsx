import { Link } from 'react-router-dom'
import useUiStore from '../store/uiStore'

function SettingRow({ label, value, children }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-4 py-3 border-b border-border last:border-0">
      <dt className="text-sm font-mono text-muted">{label}</dt>
      <dd className="text-sm font-mono text-white min-w-0">{children ?? value}</dd>
    </div>
  )
}

export default function Settings() {
  const {
    compactMode,
    refreshIntervalSeconds,
    setCompactMode,
    setRefreshIntervalSeconds,
  } = useUiStore()

  const apiUrl =
    import.meta.env.VITE_API_URL ||
    (import.meta.env.DEV ? 'http://localhost:8000/api' : 'Same origin')
  const wsUrl =
    import.meta.env.VITE_WS_URL ||
    (import.meta.env.DEV ? 'ws://localhost:8000/ws/incidents/' : 'Same origin')

  return (
    <div className="p-6 max-w-2xl">
      <div className="mb-6">
        <h1 className="font-mono text-xl font-bold text-white">Settings</h1>
        <p className="text-muted text-sm mt-1">
          Client preferences and connection info. Secrets are never stored here.
        </p>
      </div>

      <div className="rounded-lg border border-border bg-surface overflow-hidden">
        <div className="px-5 py-3 border-b border-border">
          <h2 className="font-mono font-semibold text-white">Connection</h2>
        </div>
        <dl className="px-5 divide-y divide-border">
          <SettingRow
            label="API base URL"
            value={apiUrl}
          >
            <span className="truncate block max-w-[280px]" title={apiUrl}>{apiUrl}</span>
          </SettingRow>
          <SettingRow
            label="WebSocket URL"
            value={wsUrl}
          >
            <span className="truncate block max-w-[280px]" title={wsUrl}>{wsUrl}</span>
          </SettingRow>
        </dl>
      </div>

      <div className="rounded-lg border border-border bg-surface overflow-hidden mt-6">
        <div className="px-5 py-3 border-b border-border">
          <h2 className="font-mono font-semibold text-white">Preferences</h2>
        </div>
        <dl className="px-5 divide-y divide-border">
          <SettingRow label="Compact mode">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={compactMode}
                onChange={(e) => setCompactMode(e.target.checked)}
                className="rounded border-border bg-surface2 text-accent focus:ring-accent"
              />
              <span className="text-sm font-mono text-white">Use compact layouts</span>
            </label>
          </SettingRow>
          <SettingRow label="Status refresh (seconds)">
            <select
              value={refreshIntervalSeconds}
              onChange={(e) => setRefreshIntervalSeconds(Number(e.target.value))}
              className="rounded border border-border bg-surface2 px-2 py-1.5 text-sm font-mono text-white"
            >
              {[15, 30, 60, 120].map((n) => (
                <option key={n} value={n}>{n}s</option>
              ))}
            </select>
          </SettingRow>
        </dl>
      </div>

      <div className="mt-6 rounded-lg border border-border bg-surface p-5">
        <h2 className="font-mono font-semibold text-white mb-2">Cluster</h2>
        <p className="text-muted text-sm font-mono mb-3">
          Connect or manage Kubernetes clusters used for incident ingestion.
        </p>
        <Link
          to="/connect"
          className="inline-flex items-center gap-2 px-4 py-2 rounded bg-accent text-bg font-mono text-sm hover:opacity-90"
        >
          Connect Cluster
        </Link>
      </div>
    </div>
  )
}
