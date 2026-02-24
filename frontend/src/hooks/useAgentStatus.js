import { useQuery } from '@tanstack/react-query'
import { fetchAgentStatus } from '../api/agents'

export function useAgentStatus() {
  return useQuery({
    queryKey: ['agentStatus'],
    queryFn: fetchAgentStatus,
    staleTime: 15000,
  })
}
