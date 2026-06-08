import client from './client'

export function fetchNotificationConfigs() {
  return client.get('/notifications/configs/').then((r) => r.data)
}

export function createNotificationConfig(payload) {
  return client.post('/notifications/configs/', payload).then((r) => r.data)
}

export function updateNotificationConfig(id, payload) {
  return client.patch(`/notifications/configs/${id}/`, payload).then((r) => r.data)
}

export function deleteNotificationConfig(id) {
  return client.delete(`/notifications/configs/${id}/`)
}
