import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { fetchIncidents, fetchIncident, submitFix } from '../api/incidents'

export function useIncidents(params = {}) {
  return useQuery({
    queryKey: ['incidents', params],
    queryFn: () => fetchIncidents(params),
    refetchInterval: 30000,
    staleTime: 10000,
  })
}

export function useIncident(id) {
  return useQuery({
    queryKey: ['incident', id],
    queryFn: () => fetchIncident(id),
    enabled: !!id,
    refetchInterval: (query) => {
      const data = query.state.data
      return data?.ai_analysis ? false : 5000
    },
  })
}

export function useSubmitFix(incidentId) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data) => submitFix(incidentId, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['incident', incidentId])
      toast.success('Fix submitted! Corrective RAG updated.')
    },
    onError: (err) => {
      toast.error(err.response?.data?.detail || err.message || 'Failed to submit fix')
    },
  })
}
