import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { fetchClusters, deleteCluster, stopWatcher } from '../../api/clusters'
import { clearIncidentHistory } from '../../api/incidents'
import useIncidentStore from '../../store/incidentStore'
import TopBar from './TopBar'
import clsx from 'clsx'

const navItems = [
  { to: '/', label: 'Dashboard', icon: '🏠' },
  { to: '/incidents', label: 'Incidents', icon: '🚨' },
  { to: '/graph', label: 'Graph Explorer', icon: '🕸️' },
  { to: '/patterns', label: 'Patterns', icon: '📊' },
  { to: '/risk-check', label: 'Risk Check', icon: '⚠️' },
  { to: '/chat', label: 'Cluster Assistant', icon: '💬' },
]

const systemItems = [
  { to: '/status', label: 'AI Status', icon: '🤖' },
  { to: '/settings', label: 'Settings', icon: '⚙️' },
]

export default function AppShell() {
  const queryClient = useQueryClient()
  const clearLive = useIncidentStore((s) => s.clearLive)
  const [disconnectMenu, setDisconnectMenu] = useState(null) // cluster id or null

  const { data: clusters } = useQuery({
    queryKey: ['clusters'],
    queryFn: fetchClusters,
  })
  const list = Array.isArray(clusters) ? clusters : (clusters?.results || [])
  const activeCluster = list.find((c) => c.status === 'watching' || c.status === 'connected') || list[0]
  const hasCluster = list.length > 0
  const isWatching = activeCluster?.status === 'watching'

  const deleteClusterMutation = useMutation({
    mutationFn: deleteCluster,
    onSuccess: () => {
      queryClient.invalidateQueries(['clusters'])
      setDisconnectMenu(null)
      stopWatcher().catch(() => {})
      toast.success('Cluster disconnected.')
    },
    onError: (err) => {
      setDisconnectMenu(null)
      toast.error(err.response?.data?.detail || err.message || 'Failed to disconnect')
    },
  })

  const clearHistoryMutation = useMutation({
    mutationFn: clearIncidentHistory,
    onSuccess: () => {
      queryClient.invalidateQueries(['incidents'])
      clearLive()
      setDisconnectMenu(null)
      toast.success('All incidents cleared. App reset to null state.')
    },
    onError: (err) => {
      setDisconnectMenu(null)
      toast.error(err.response?.data?.error || err.message || 'Failed to clear incidents')
    },
  })

  const handleDisconnectOnly = (clusterId) => {
    deleteClusterMutation.mutate(clusterId)
  }

  const handleDisconnectAndClear = (clusterId) => {
    deleteClusterMutation.mutate(clusterId, {
      onSuccess: () => {
        clearHistoryMutation.mutate()
      },
    })
  }

  return (
    <div className="min-h-screen flex flex-col bg-bg">
      <TopBar />
      <div className="flex flex-1 overflow-hidden">
        <aside className="w-52 shrink-0 border-r border-border bg-surface flex flex-col">
          <div className="p-3 border-b border-border">
            <span className="font-mono text-sm font-semibold text-white">⬡ KubeMemory</span>
          </div>
          <nav className="p-2 flex flex-col gap-0.5 mt-2">
            {navItems.map(({ to, label, icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  clsx(
                    'px-3 py-2 rounded text-sm font-mono transition-colors flex items-center gap-2',
                    isActive
                      ? 'bg-accent/20 text-accent'
                      : 'text-muted hover:text-white hover:bg-surface2'
                  )
                }
              >
                <span>{icon}</span>
                {label}
              </NavLink>
            ))}
          </nav>
          <div className="border-t border-border my-2" />
          <div className="px-3 py-1.5 text-xs font-mono text-muted uppercase tracking-wider">Cluster</div>
          <nav className="p-2 flex flex-col gap-0.5">
            {list.length === 0 && (
              <p className="px-3 py-1.5 text-xs font-mono text-muted">No cluster connected</p>
            )}
            {list.map((c) => (
              <div
                key={c.id}
                className="group flex items-center gap-1 rounded px-2 py-1.5 hover:bg-surface2/50"
              >
                <span
                  className={clsx(
                    'w-2 h-2 rounded-full flex-shrink-0',
                    (c.status === 'watching' || c.status === 'connected') && 'bg-accent',
                    c.status === 'watching' && 'animate-pulse',
                    c.status === 'failed' && 'bg-accent-red',
                    c.status === 'pending' && 'bg-surface2'
                  )}
                />
                <span className="truncate flex-1 text-sm font-mono text-white">{c.name}</span>
                <div className="relative">
                  <button
                    type="button"
                    onClick={() => setDisconnectMenu(disconnectMenu === c.id ? null : c.id)}
                    className="opacity-60 hover:opacity-100 text-muted hover:text-white p-0.5 rounded"
                    title="Disconnect cluster"
                    aria-label="Disconnect cluster"
                  >
                    ⊗
                  </button>
                  {disconnectMenu === c.id && (
                    <div className="absolute left-0 top-full mt-1 z-50 min-w-[200px] rounded border border-border bg-surface shadow-lg p-2 space-y-1">
                      <p className="text-xs text-muted font-mono mb-2">Disconnect &quot;{c.name}&quot;</p>
                      <button
                        type="button"
                        className="w-full text-left px-2 py-1.5 rounded text-sm font-mono text-white hover:bg-surface2"
                        onClick={() => handleDisconnectOnly(c.id)}
                        disabled={deleteClusterMutation.isPending}
                      >
                        Disconnect only
                      </button>
                      <button
                        type="button"
                        className="w-full text-left px-2 py-1.5 rounded text-sm font-mono text-accent hover:bg-surface2"
                        onClick={() => handleDisconnectAndClear(c.id)}
                        disabled={deleteClusterMutation.isPending || clearHistoryMutation.isPending}
                      >
                        Disconnect and clear all incidents
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}
            <NavLink
              to="/connect"
              className={({ isActive }) =>
                clsx(
                  'px-3 py-2 rounded text-sm font-mono transition-colors flex items-center gap-2',
                  isActive ? 'bg-accent/20 text-accent' : 'text-muted hover:text-white hover:bg-surface2',
                  !hasCluster && 'text-orange-400'
                )
              }
            >
              <span className={!hasCluster ? 'animate-pulse' : ''}>+</span>
              Connect Cluster
            </NavLink>
          </nav>
          <div className="border-t border-border my-2" />
          <div className="px-3 py-1.5 text-xs font-mono text-muted uppercase tracking-wider">System</div>
          <nav className="p-2 flex flex-col gap-0.5">
            {systemItems.map(({ to, label, icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  clsx(
                    'px-3 py-2 rounded text-sm font-mono transition-colors flex items-center gap-2',
                    isActive
                      ? 'bg-accent/20 text-accent'
                      : 'text-muted hover:text-white hover:bg-surface2'
                  )
                }
              >
                <span>{icon}</span>
                {label}
              </NavLink>
            ))}
          </nav>
        </aside>
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
