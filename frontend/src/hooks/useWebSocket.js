import { useEffect, useRef, useCallback } from 'react'
import useIncidentStore from '../store/incidentStore'
import toast from 'react-hot-toast'

export function useWebSocket() {
  const ws = useRef(null)
  const reconnectTimeout = useRef(null)
  const { addLiveIncident, setWsConnected } = useIncidentStore()

  const connect = useCallback(() => {
    const url = import.meta.env.VITE_WS_URL + '/incidents/'
    ws.current = new WebSocket(url)

    ws.current.onopen = () => {
      setWsConnected(true)
      console.log('[WS] Connected to KubeMemory')
    }

    ws.current.onmessage = (e) => {
      const msg = JSON.parse(e.data)
      if (msg.type === 'new_incident') {
        addLiveIncident(msg.data)
        if (msg.data.severity === 'critical') {
          toast.error(`🔴 Critical: ${msg.data.pod_name} in ${msg.data.namespace}`)
        } else if (msg.data.severity === 'high') {
          toast(`⚠️ ${msg.data.incident_type}: ${msg.data.pod_name}`)
        }
      }
    }

    ws.current.onclose = () => {
      setWsConnected(false)
      // Auto-reconnect after 3 seconds
      reconnectTimeout.current = setTimeout(connect, 3000)
    }

    ws.current.onerror = (err) => {
      console.error('[WS] Error:', err)
      ws.current?.close()
    }
  }, [addLiveIncident, setWsConnected])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(reconnectTimeout.current)
      ws.current?.close()
    }
  }, [connect])
}
