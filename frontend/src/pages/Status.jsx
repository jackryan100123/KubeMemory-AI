import { useAgentStatus } from '../hooks/useAgentStatus'
import { useWatcherStatus } from '../hooks/useWatcherStatus'
import { useSystemStatus } from '../hooks/useSystemStatus'
import { useQuery } from '@tanstack/react-query'
import { fetchClusters } from '../api/clusters'
import useUiStore from '../store/uiStore'
import LoadingSpinner from '../components/shared/LoadingSpinner'
import ErrorBoundary from '../components/shared/ErrorBoundary'

function StatusCard({ title, icon, children, status, statusLabel }) {
  const isOk = status === 'ok'
  const isDegraded = status === 'degraded'
  const isStopped = status === 'stopped'
  const isUnknown = status === 'unknown'
  const label =
    statusLabel ??
    (isOk ? 'Ready' : isDegraded ? 'Degraded' : isStopped ? 'Stopped' : isUnknown ? '…' : 'Unknown')
  return (
    <div className="rounded-lg border border-border bg-surface p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-mono font-semibold text-white flex items-center gap-2">
          <span>{icon}</span>
          {title}
        </h3>
        <span
          className={`text-xs font-mono uppercase tracking-wider px-2 py-1 rounded ${
            isOk
              ? 'bg-accent/20 text-accent'
              : isDegraded
                ? 'bg-accent-red/20 text-accent-red'
                : 'bg-surface2 text-muted'
          }`}
        >
          {label}
        </span>
      </div>
      {children}
    </div>
  )
}

export default function Status() {
  const refreshIntervalSeconds = useUiStore((s) => s.refreshIntervalSeconds)
  const refetchInterval = refreshIntervalSeconds * 1000
  const { data: systemStatus, isLoading: statusLoading } = useSystemStatus({ refetchInterval })
  const { data: agentStatus, isLoading: agentLoading, error: agentError } = useAgentStatus({
    refetchInterval,
  })
  const { data: watcherData, isLoading: watcherLoading, error: watcherError } = useWatcherStatus({
    refetchInterval,
  })
  const { data: clusters } = useQuery({
    queryKey: ['clusters'],
    queryFn: fetchClusters,
  })
  const clusterList = Array.isArray(clusters) ? clusters : clusters?.results || []
  const activeCluster =
    watcherData?.cluster_id != null
      ? clusterList.find((c) => c.id === watcherData.cluster_id)
      : null

  const ollamaReady = systemStatus?.ollama_ready ?? agentStatus?.ollama_ready
  const pipelineStatus =
    agentError || agentStatus === undefined
      ? 'unknown'
      : ollamaReady && agentStatus?.chroma_doc_count !== undefined
        ? 'ok'
        : 'degraded'

  const heartbeatAge = systemStatus?.watcher_heartbeat_age_seconds
  const watcherHealthy = systemStatus?.watcher_healthy === true
  const watcherStatusValue =
    watcherError || watcherData === undefined
      ? 'unknown'
      : watcherData?.running && watcherHealthy
        ? 'ok'
        : watcherData?.running
          ? 'degraded'
          : 'stopped'

  const failedTasks = systemStatus?.failed_tasks || []

  if ((agentLoading && !agentStatus) || (statusLoading && !systemStatus)) {
    return (
      <div className="p-6 flex items-center justify-center min-h-[200px]">
        <LoadingSpinner className="h-8 w-8" />
      </div>
    )
  }

  return (
    <ErrorBoundary>
      <div className="p-6 space-y-6">
        <div>
          <h1 className="font-mono text-xl font-bold text-white">Status</h1>
          <p className="text-muted text-sm mt-1">
            Pipeline, watcher heartbeats, and failed background tasks.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <StatusCard title="AI Pipeline" icon="🤖" status={pipelineStatus}>
            <dl className="space-y-2 text-sm font-mono">
              <div className="flex justify-between">
                <dt className="text-muted">Ollama ready</dt>
                <dd className={ollamaReady ? 'text-accent' : 'text-accent-red'}>
                  {ollamaReady === true ? 'Yes' : ollamaReady === false ? 'No' : '—'}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted">Model (reasoning)</dt>
                <dd className="text-white">{agentStatus?.model ?? systemStatus?.model ?? '—'}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted">ChromaDB docs</dt>
                <dd className="text-white">
                  {agentStatus?.chroma_doc_count ?? systemStatus?.chroma_doc_count ?? '—'}
                </dd>
              </div>
            </dl>
          </StatusCard>

          <StatusCard
            title="Cluster Watcher"
            icon="⬡"
            status={watcherStatusValue}
            statusLabel={
              watcherHealthy
                ? 'Healthy'
                : watcherData?.running
                  ? 'No heartbeat'
                  : undefined
            }
          >
            {watcherLoading && !watcherData ? (
              <div className="flex items-center gap-2 text-muted text-sm font-mono">
                <LoadingSpinner className="h-4 w-4" />
                Checking…
              </div>
            ) : (
              <dl className="space-y-2 text-sm font-mono">
                <div className="flex justify-between">
                  <dt className="text-muted">Process</dt>
                  <dd className={watcherData?.running ? 'text-accent' : 'text-muted'}>
                    {watcherData?.running ? 'Running' : 'Stopped'}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted">Heartbeat age</dt>
                  <dd
                    className={
                      heartbeatAge != null && heartbeatAge < 45 ? 'text-accent' : 'text-accent-red'
                    }
                  >
                    {heartbeatAge != null ? `${Math.round(heartbeatAge)}s` : '—'}
                  </dd>
                </div>
                {activeCluster && (
                  <div className="flex justify-between">
                    <dt className="text-muted">Cluster</dt>
                    <dd className="text-white">{activeCluster.name}</dd>
                  </div>
                )}
              </dl>
            )}
          </StatusCard>
        </div>

        <div className="rounded-lg border border-border bg-surface p-5">
          <h3 className="font-mono font-semibold text-white mb-4">Failed tasks (last 50)</h3>
          {failedTasks.length === 0 ? (
            <p className="text-muted text-sm font-mono">No recent task failures.</p>
          ) : (
            <ul className="space-y-2 max-h-64 overflow-y-auto">
              {failedTasks.map((t) => (
                <li
                  key={t.id}
                  className="text-xs font-mono border border-border rounded p-2 bg-bg"
                >
                  <span className="text-accent-red uppercase">{t.status}</span>{' '}
                  <span className="text-white">{t.task_name}</span>
                  <p className="text-muted mt-1 truncate">{t.error_message}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </ErrorBoundary>
  )
}
