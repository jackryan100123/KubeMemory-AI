import { useQuery } from '@tanstack/react-query'
import { watcherStatus } from '../api/clusters'

/**
 * Fetches cluster watcher status (running, cluster_id).
 * @param {{ refetchInterval?: number }} options - Optional refetchInterval in ms (e.g. from Settings).
 */
export function useWatcherStatus(options = {}) {
  return useQuery({
    queryKey: ['watcherStatus'],
    queryFn: watcherStatus,
    staleTime: 10000,
    refetchInterval: options.refetchInterval,
  })
}
