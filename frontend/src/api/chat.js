/**
 * Chat API: sessions, messages (SSE), suggestions, commands.
 * All requests go through the same API base as the rest of the app.
 */
import client from './client'

const apiBase =
  import.meta.env.VITE_API_URL ||
  (import.meta.env.DEV ? 'http://localhost:8000/api' : null) ||
  (typeof window !== 'undefined' ? `${window.location.origin}/api` : 'http://localhost:8000/api')

const DEBUG_CHAT = true

export const createSession = (namespace = 'all') =>
  client.post('/chat/sessions/', { namespace }).then((r) => {
    if (DEBUG_CHAT) console.log('[chat] POST /sessions/ created id=', r.data?.id, 'namespace=', namespace)
    return r.data
  })

export const listSessions = () =>
  client.get('/chat/sessions/').then((r) => {
    const data = r.data
    const list = Array.isArray(data) ? data : []
    const totalInDb = r.headers?.['x-chat-total-in-db']
    if (DEBUG_CHAT) {
      console.log('[chat] GET /sessions/ response count=', list.length, 'X-Chat-Total-In-DB=', totalInDb, 'ids=', list.slice(0, 5).map((s) => s.id))
    }
    return list
  })

export const getSession = (id) =>
  client.get(`/chat/sessions/${id}/`).then((r) => r.data)

export const deleteSession = (id) =>
  client.delete(`/chat/sessions/${id}/`).then((r) => {
    if (DEBUG_CHAT) console.log('[chat] DELETE /sessions/' + id + '/ status=', r.status)
    return r
  })

/** Delete all chat sessions. Requires backend DELETE /chat/sessions/?all=1 */
export const deleteAllSessions = () =>
  client.delete('/chat/sessions/', { params: { all: '1' } }).then((r) => r.data)

export const getSuggestions = (namespace) =>
  client.get(`/chat/suggestions/?ns=${encodeURIComponent(namespace || 'all')}`).then((r) => r.data)

export const getCommands = () =>
  client.get('/chat/commands/').then((r) => r.data)

/**
 * Send a message and consume SSE stream. Calls onEvent for each event.
 * Events: { type: 'token'|'tool_call'|'tool_result'|'done'|'error', ... }
 */
export function sendMessage(sessionId, message, onEvent) {
  return fetch(`${apiBase}/chat/sessions/${sessionId}/message/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  }).then((response) => {
    if (!response.ok) {
      return response.json().then(
        (data) => Promise.reject(new Error(data.error || response.statusText)),
        () => Promise.reject(new Error(response.statusText))
      )
    }
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    function pump() {
      return reader.read().then(({ done, value }) => {
        if (done) return
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data === '[STREAM_END]') return
            try {
              onEvent(JSON.parse(data))
            } catch (_) { /* ignore parse errors */ }
          }
        }
        return pump()
      })
    }
    return pump()
  })
}
