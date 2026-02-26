import { useQuery } from '@tanstack/react-query'
import { fetchGraphData } from '../api/memory'

export function useGraphData(namespace) {
  return useQuery({
    queryKey: ['graph', namespace ?? 'default'],
    queryFn: () => fetchGraphData(namespace || 'default'),
    staleTime: 60000,
    retry: 2,
    retryDelay: (attemptIndex) => Math.min(2000 * 2 ** attemptIndex, 10000),
    enabled: true,
  })
}
