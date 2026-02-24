import { useQuery } from '@tanstack/react-query'
import { fetchPatterns } from '../api/incidents'

export function usePatterns() {
  return useQuery({
    queryKey: ['patterns'],
    queryFn: fetchPatterns,
    staleTime: 60000,
  })
}
