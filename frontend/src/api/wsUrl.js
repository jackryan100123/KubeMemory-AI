/**
 * Build a WebSocket URL for Django Channels paths (e.g. incidents/, chat/).
 * Supports VITE_WS_URL as full ws(s) URL, host-only, or relative /ws prefix.
 */
export function buildWebSocketUrl(channelPath) {
  const normalizedPath = channelPath.replace(/^\/+/, '').replace(/\/+$/, '')
  const raw =
    import.meta.env.VITE_WS_URL ||
    (import.meta.env.DEV ? 'ws://localhost:8000' : null) ||
    (typeof window !== 'undefined'
      ? `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`
      : 'ws://localhost:8000')

  if (typeof raw === 'string' && (raw.startsWith('ws://') || raw.startsWith('wss://'))) {
    const base = raw.replace(/\/ws\/?$/, '').replace(/\/+$/, '')
    return `${base}/ws/${normalizedPath}/`
  }

  const hostBase =
    typeof window !== 'undefined'
      ? `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`
      : 'ws://localhost:8000'
  const wsPrefix =
    typeof raw === 'string' && raw.startsWith('/')
      ? raw.replace(/\/+$/, '')
      : '/ws'
  return `${hostBase}${wsPrefix}/${normalizedPath}/`
}
