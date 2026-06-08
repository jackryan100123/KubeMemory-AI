import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import {
  createNotificationConfig,
  deleteNotificationConfig,
  fetchNotificationConfigs,
} from '../api/notifications'
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

      <NotificationsSection />

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

function NotificationsSection() {
  const queryClient = useQueryClient()
  const [type, setType] = useState('webhook')
  const [url, setUrl] = useState('')
  const [minSeverity, setMinSeverity] = useState('high')

  const { data } = useQuery({
    queryKey: ['notification-configs'],
    queryFn: fetchNotificationConfigs,
  })
  const list = Array.isArray(data) ? data : data?.results || []

  const createMutation = useMutation({
    mutationFn: createNotificationConfig,
    onSuccess: () => {
      queryClient.invalidateQueries(['notification-configs'])
      setUrl('')
      toast.success('Notification sink added')
    },
    onError: (err) => toast.error(err.message || 'Failed to save'),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteNotificationConfig,
    onSuccess: () => {
      queryClient.invalidateQueries(['notification-configs'])
      toast.success('Removed')
    },
  })

  return (
    <div className="rounded-lg border border-border bg-surface overflow-hidden mt-6">
      <div className="px-5 py-3 border-b border-border">
        <h2 className="font-mono font-semibold text-white">Notifications</h2>
        <p className="text-muted text-xs font-mono mt-1">
          Slack or webhook alerts when incidents meet minimum severity.
        </p>
      </div>
      <div className="px-5 py-4 space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <select
            value={type}
            onChange={(e) => setType(e.target.value)}
            className="rounded border border-border bg-surface2 px-2 py-2 text-sm font-mono text-white"
          >
            <option value="webhook">Webhook</option>
            <option value="slack">Slack</option>
          </select>
          <select
            value={minSeverity}
            onChange={(e) => setMinSeverity(e.target.value)}
            className="rounded border border-border bg-surface2 px-2 py-2 text-sm font-mono text-white"
          >
            <option value="low">low+</option>
            <option value="medium">medium+</option>
            <option value="high">high+</option>
            <option value="critical">critical</option>
          </select>
          <input
            type="url"
            placeholder="https://webhook.site/..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="rounded border border-border bg-surface2 px-2 py-2 text-sm font-mono text-white col-span-full sm:col-span-1"
          />
        </div>
        <button
          type="button"
          disabled={!url.trim() || createMutation.isPending}
          onClick={() =>
            createMutation.mutate({
              type,
              url: url.trim(),
              min_severity: minSeverity,
              enabled: true,
            })
          }
          className="px-4 py-2 rounded bg-accent text-bg font-mono text-sm disabled:opacity-50"
        >
          Add notification
        </button>
        {list.length > 0 && (
          <ul className="space-y-2 pt-2 border-t border-border">
            {list.map((cfg) => (
              <li
                key={cfg.id}
                className="flex justify-between items-center text-xs font-mono gap-2"
              >
                <span className="text-white truncate">
                  {cfg.type} · {cfg.min_severity}+ · {cfg.url}
                </span>
                <button
                  type="button"
                  onClick={() => deleteMutation.mutate(cfg.id)}
                  className="text-accent-red shrink-0"
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
