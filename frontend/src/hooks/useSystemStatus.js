import { useQuery } from '@tanstack/react-query'
import { fetchSystemStatus } from '../api/status'

export function useSystemStatus(options = {}) {
  return useQuery({
    queryKey: ['system-status'],
    queryFn: fetchSystemStatus,
    ...options,
  })
}
