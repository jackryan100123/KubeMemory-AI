import { useEffect, useRef, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import useIncidentStore from '../store/incidentStore'
import toast from 'react-hot-toast'

export function useWebSocket() {
  const ws = useRef(null)
  const reconnectTimeout = useRef(null)
  const queryClient = useQueryClient()
  const { addLiveIncident, setWsConnected } = useIncidentStore()

  const connect = useCallback(() => {
    // When built in Docker, use same origin so nginx can proxy /ws to backend
    const wsBase =
      import.meta.env.VITE_WS_URL ||
      (typeof window !== 'undefined'
        ? `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`
        : 'ws://localhost:8000')
    const url = wsBase + '/ws/incidents/'
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
      } else if (msg.type === 'analysis_complete' && msg.incident_id) {
        queryClient.invalidateQueries(['incident', msg.incident_id])
        queryClient.invalidateQueries(['analysis', msg.incident_id])
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
  }, [addLiveIncident, setWsConnected, queryClient])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(reconnectTimeout.current)
      ws.current?.close()
    }
  }, [connect])
}
