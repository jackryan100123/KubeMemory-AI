import { NavLink, Outlet } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchClusters } from '../../api/clusters'
import TopBar from './TopBar'
import clsx from 'clsx'

const navItems = [
  { to: '/', label: 'Dashboard', icon: '🏠' },
  { to: '/incidents', label: 'Incidents', icon: '🚨' },
  { to: '/graph', label: 'Graph Explorer', icon: '🕸️' },
  { to: '/patterns', label: 'Patterns', icon: '📊' },
  { to: '/risk-check', label: 'Risk Check', icon: '⚠️' },
]

const systemItems = [
  { to: '/status', label: 'AI Status', icon: '🤖' },
  { to: '/settings', label: 'Settings', icon: '⚙️' },
]

export default function AppShell() {
  const { data: clusters } = useQuery({
    queryKey: ['clusters'],
    queryFn: fetchClusters,
  })
  const list = Array.isArray(clusters) ? clusters : (clusters?.results || [])
  const activeCluster = list.find((c) => c.status === 'watching' || c.status === 'connected') || list[0]
  const hasCluster = list.length > 0
  const isWatching = activeCluster?.status === 'watching'

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
            {activeCluster ? (
              <div className="px-3 py-2 flex items-center gap-2 text-sm font-mono text-white">
                <span
                  className={clsx(
                    'w-2 h-2 rounded-full flex-shrink-0',
                    isWatching && 'bg-accent animate-pulse',
                    activeCluster.status === 'connected' && !isWatching && 'bg-orange-500',
                    activeCluster.status === 'failed' && 'bg-accent-red',
                    activeCluster.status === 'pending' && 'bg-surface2'
                  )}
                />
                <span className="truncate">{activeCluster.name}</span>
              </div>
            ) : null}
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
