import { useQuery } from '@tanstack/react-query'
import { fetchAnalysis } from '../api/agents'

export function useAnalysis(incidentId) {
  return useQuery({
    queryKey: ['analysis', incidentId],
    queryFn: () => fetchAnalysis(incidentId),
    enabled: !!incidentId,
    refetchInterval: (query) => {
      const data = query.state.data
      return data?.status === 'ok' ? false : 5000
    },
  })
}
