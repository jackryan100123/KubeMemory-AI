import client from './client'

export function fetchSystemStatus() {
  return client.get('/status/').then((r) => r.data)
}
