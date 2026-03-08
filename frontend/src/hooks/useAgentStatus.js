import { useQuery } from '@tanstack/react-query'
import { fetchAgentStatus } from '../api/agents'

/**
 * @param {{ refetchInterval?: number }} options - Optional refetchInterval in ms (e.g. from Settings).
 */
export function useAgentStatus(options = {}) {
  return useQuery({
    queryKey: ['agentStatus'],
    queryFn: fetchAgentStatus,
    staleTime: 15000,
    refetchInterval: options.refetchInterval,
  })
}
