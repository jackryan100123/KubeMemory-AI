import { useQuery } from '@tanstack/react-query'
import { fetchGraphData } from '../api/memory'

export function useGraphData(namespace) {
  return useQuery({
    queryKey: ['graph', namespace ?? 'default'],
    queryFn: () => fetchGraphData(namespace || 'default'),
    staleTime: 60000,
    enabled: true,
  })
}
