import { useAgentStatus } from '../hooks/useAgentStatus'
import { useWatcherStatus } from '../hooks/useWatcherStatus'
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
  const label = statusLabel ?? (isOk ? 'Ready' : isDegraded ? 'Degraded' : isStopped ? 'Stopped' : isUnknown ? '…' : 'Unknown')
  return (
    <div className="rounded-lg border border-border bg-surface p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-mono font-semibold text-white flex items-center gap-2">
          <span>{icon}</span>
          {title}
        </h3>
        <span
          className={`text-xs font-mono uppercase tracking-wider px-2 py-1 rounded ${
            isOk ? 'bg-accent/20 text-accent' : isDegraded ? 'bg-accent-red/20 text-accent-red' : isStopped ? 'bg-surface2 text-muted' : 'bg-surface2 text-muted'
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
  const clusterList = Array.isArray(clusters) ? clusters : (clusters?.results || [])
  const activeCluster = watcherData?.cluster_id != null
    ? clusterList.find((c) => c.id === watcherData.cluster_id)
    : null

  const pipelineStatus =
    agentError || agentStatus === undefined
      ? 'unknown'
      : agentStatus?.ollama_ok && agentStatus?.chroma_doc_count !== undefined
        ? 'ok'
        : 'degraded'

  const watcherStatusValue =
    watcherError || watcherData === undefined
      ? 'unknown'
      : watcherData?.running
        ? 'ok'
        : 'stopped'

  if (agentLoading && !agentStatus) {
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
            Pipeline and cluster watcher status. Refreshes automatically.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <StatusCard title="AI Pipeline" icon="🤖" status={pipelineStatus}>
            <dl className="space-y-2 text-sm font-mono">
              <div className="flex justify-between">
                <dt className="text-muted">Ollama</dt>
                <dd className={agentStatus?.ollama_ok ? 'text-accent' : 'text-accent-red'}>
                  {agentStatus?.ollama_ok === true ? 'Connected' : agentStatus?.ollama_ok === false ? 'Unreachable' : '—'}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted">Model</dt>
                <dd className="text-white">{agentStatus?.model ?? '—'}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted">Ollama URL</dt>
                <dd className="text-white truncate max-w-[180px]" title={agentStatus?.ollama_base_url}>
                  {agentStatus?.ollama_base_url ?? '—'}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted">ChromaDB docs</dt>
                <dd className="text-white">
                  {agentStatus?.chroma_doc_count !== undefined && agentStatus?.chroma_doc_count !== null
                    ? agentStatus.chroma_doc_count
                    : '—'}
                </dd>
              </div>
            </dl>
          </StatusCard>

          <StatusCard title="Cluster Watcher" icon="⬡" status={watcherStatusValue}>
            {watcherLoading && !watcherData ? (
              <div className="flex items-center gap-2 text-muted text-sm font-mono">
                <LoadingSpinner className="h-4 w-4" />
                Checking…
              </div>
            ) : (
              <>
                <dl className="space-y-2 text-sm font-mono">
                  <div className="flex justify-between">
                    <dt className="text-muted">State</dt>
                    <dd className={watcherData?.running ? 'text-accent' : 'text-muted'}>
                      {watcherData?.running ? 'Running' : 'Stopped'}
                    </dd>
                  </div>
                  {watcherData?.cluster_id != null && (
                    <div className="flex justify-between">
                      <dt className="text-muted">Cluster</dt>
                      <dd className="text-white">
                        {activeCluster?.name ?? `ID ${watcherData.cluster_id}`}
                      </dd>
                    </div>
                  )}
                </dl>
                {watcherStatusValue === 'stopped' && (
                  <p className="text-muted text-xs font-mono mt-3 pt-3 border-t border-border">
                    Start the watcher from <strong className="text-white">Connect Cluster</strong> to begin ingesting cluster events.
                  </p>
                )}
              </>
            )}
          </StatusCard>
        </div>
      </div>
    </ErrorBoundary>
  )
}
