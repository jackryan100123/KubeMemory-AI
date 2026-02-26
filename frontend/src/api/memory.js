import client from './client'

/** Graph can be slow (Neo4j); use longer timeout and retry. */
export const fetchGraphData = (namespace = 'default') =>
  client.get('/memory/graph/', { params: { namespace }, timeout: 60000 }).then((r) => r.data)

export const fetchBlastRadius = (pod, namespace = 'default') =>
  client.get('/memory/blast-radius/', { params: { pod, namespace } }).then((r) => r.data)

export const fetchMemoryPatterns = () =>
  client.get('/memory/patterns/').then((r) => r.data)
