import { useEffect, useRef, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { buildWebSocketUrl } from '../api/wsUrl'
import useIncidentStore from '../store/incidentStore'
import toast from 'react-hot-toast'

const MAX_RECONNECT_MS = 30000

export function useWebSocket() {
  const ws = useRef(null)
  const reconnectTimeout = useRef(null)
  const reconnectDelay = useRef(3000)
  const queryClient = useQueryClient()
  const { addLiveIncident, setWsConnected } = useIncidentStore()

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN || ws.current?.readyState === WebSocket.CONNECTING) {
      return
    }

    const url = buildWebSocketUrl('incidents')
    ws.current = new WebSocket(url)

    ws.current.onopen = () => {
      reconnectDelay.current = 3000
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
      const delay = reconnectDelay.current
      reconnectDelay.current = Math.min(delay * 2, MAX_RECONNECT_MS)
      reconnectTimeout.current = setTimeout(connect, delay)
    }

    ws.current.onerror = () => {
      ws.current?.close()
    }
  }, [addLiveIncident, setWsConnected, queryClient])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(reconnectTimeout.current)
      ws.current?.close()
      ws.current = null
    }
  }, [connect])
}
