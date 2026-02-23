import client from './client'

export const fetchIncidents = (params = {}) =>
  client.get('/incidents/', { params }).then(r => r.data)

export const fetchIncident = (id) =>
  client.get(`/incidents/${id}/`).then(r => r.data)

export const updateIncidentStatus = (id, status) =>
  client.patch(`/incidents/${id}/`, { status }).then(r => r.data)

export const submitFix = (incidentId, data) =>
  client.post(`/incidents/${incidentId}/fixes/`, data).then(r => r.data)

export const fetchPatterns = () =>
  client.get('/incidents/patterns/').then(r => r.data)
