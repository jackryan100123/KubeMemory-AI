import client from './client'

export const fetchClusters = () =>
  client.get('/clusters/').then((r) => r.data)

export const createCluster = (data) =>
  client.post('/clusters/', data).then((r) => r.data)

export const fetchCluster = (id) =>
  client.get(`/clusters/${id}/`).then((r) => r.data)

export const testCluster = (id) =>
  client.post(`/clusters/${id}/test/`).then((r) => r.data)

export const connectCluster = (id) =>
  client.post(`/clusters/${id}/connect/`).then((r) => r.data)

export const fetchClusterNamespaces = (id) =>
  client.get(`/clusters/${id}/namespaces/`).then((r) => r.data)

export const deleteCluster = (id) =>
  client.delete(`/clusters/${id}/`).then((r) => r.data)

export const updateCluster = (id, data) =>
  client.patch(`/clusters/${id}/`, data).then((r) => r.data)

export const fetchClusterSecurityInfo = () =>
  client.get('/clusters/security-info/').then((r) => r.data)

export const startClusterWatcher = (clusterId) =>
  client.post(`/clusters/${clusterId}/start-watcher/`).then((r) => r.data)

export const watcherStatus = () =>
  client.get('/clusters/watcher/status/').then((r) => r.data)

export const stopWatcher = () =>
  client.post('/clusters/watcher/stop/').then((r) => r.data)
