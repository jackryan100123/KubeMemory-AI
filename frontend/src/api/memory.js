import client from './client'

export const fetchGraphData = (namespace = 'default') =>
  client.get('/memory/graph/', { params: { namespace } }).then((r) => r.data)

export const fetchBlastRadius = (pod, namespace = 'default') =>
  client.get('/memory/blast-radius/', { params: { pod, namespace } }).then((r) => r.data)

export const fetchMemoryPatterns = () =>
  client.get('/memory/patterns/').then((r) => r.data)
