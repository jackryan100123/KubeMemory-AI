import client from './client'

export const fetchAgentStatus = () =>
  client.get('/agents/status/').then((r) => r.data)

export const fetchAnalysis = (incidentId) =>
  client.get(`/agents/analysis/${incidentId}/`).then((r) => r.data)

export const triggerAnalyze = (incidentId) =>
  client.post(`/agents/analyze/${incidentId}/`, {}, { timeout: 120000 }).then((r) => r.data)

export const generateRunbook = (incidentId) =>
  client.post(`/agents/runbook/${incidentId}/`, {}, { timeout: 120000 }).then((r) => r.data)

export const fetchRiskCheck = (service, namespace) =>
  client.get('/agents/risk-check/', { params: { service, namespace } }).then((r) => r.data)
