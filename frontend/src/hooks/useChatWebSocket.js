import { useState, useCallback, useRef, useEffect } from 'react'

/**
 * WebSocket hook for the cluster chat assistant.
 * Connects to ws/chat/, sends messages, receives streamed chunks and tool_call events.
 * Pass activeClusterId so the backend can query MCP tools for that cluster.
 * @param {{ clusterId?: number | null, clusterName?: string | null }} options - Optional active cluster for MCP context
 * @returns {{
 *   messages: Array<{ role: 'user'|'assistant', content: string, toolCalls?: Array }>,
 *   sendMessage: (text: string) => void,
 *   isLoading: boolean,
 *   error: string | null,
 *   connected: boolean,
 *   clearMessages: () => void,
 * }}
 */
export function useChatWebSocket(options = {}) {
  const { clusterId = null, clusterName = null } = options
  const clusterContextRef = useRef({ clusterId, clusterName })
  clusterContextRef.current = { clusterId, clusterName }
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [connected, setConnected] = useState(false)
  const wsRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)
  const pendingContentRef = useRef('')
  const messagesRef = useRef([])
  messagesRef.current = messages

  const connect = useCallback(() => {
    const raw =
      import.meta.env.VITE_WS_URL ||
      (import.meta.env.DEV ? 'ws://localhost:8000' : null) ||
      (typeof window !== 'undefined'
        ? `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`
        : 'ws://localhost:8000')
    // Full URL (ws://host) or relative path (/ws): build ws(s)://currentHost/ws/chat/
    let wsUrl
    if (typeof raw === 'string' && (raw.startsWith('ws://') || raw.startsWith('wss://'))) {
      wsUrl = raw.replace(/\/ws\/?$/, '') + (raw.endsWith('/') ? '' : '/') + 'ws/chat/'
    } else {
      const base = typeof window !== 'undefined'
        ? (window.location.protocol === 'https:' ? 'wss:' : 'ws:') + '//' + window.location.host
        : 'ws://localhost:8000'
      const path = (typeof raw === 'string' ? raw : '/ws').replace(/\/+$/, '') + '/chat/'
      wsUrl = base + (path.startsWith('/') ? path : '/' + path)
    }
    wsRef.current = new WebSocket(wsUrl)

    wsRef.current.onopen = () => {
      setConnected(true)
      setError(null)
    }
    wsRef.current.onclose = () => {
      setConnected(false)
      reconnectTimeoutRef.current = setTimeout(connect, 3000)
    }
    wsRef.current.onerror = () => {
      console.error('[Chat] WebSocket error')
      setError('WebSocket error')
    }
    wsRef.current.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        const type = data.type
        if (type === 'chunk' && data.content) {
          pendingContentRef.current += data.content
          setMessages((prev) => {
            const last = prev[prev.length - 1]
            const isUpdatingStreaming = last?.role === 'assistant' && last?.streaming
            const rest = isUpdatingStreaming ? prev.slice(0, -1) : prev
            const next = { role: 'assistant', content: pendingContentRef.current, streaming: true }
            return [...rest, isUpdatingStreaming ? { ...last, ...next } : next]
          })
        } else if (type === 'tool_call') {
          setMessages((prev) => {
            const last = prev[prev.length - 1]
            const isUpdatingStreaming = last?.role === 'assistant' && last?.streaming
            const rest = isUpdatingStreaming ? prev.slice(0, -1) : prev
            const toolCalls = [...(last?.toolCalls || []), { name: data.name, result: data.result }]
            const next = isUpdatingStreaming
              ? { ...last, toolCalls, content: last?.content || '' }
              : { role: 'assistant', toolCalls, content: pendingContentRef.current || '', streaming: true }
            return [...rest, next]
          })
        } else if (type === 'done') {
          // Capture accumulated content before clearing to avoid race with chunk updates
          const finalContent = pendingContentRef.current || ''
          pendingContentRef.current = ''
          setMessages((prev) => {
            const last = prev[prev.length - 1]
            if (last?.role === 'assistant' && last?.streaming) {
              return [...prev.slice(0, -1), { ...last, content: finalContent || last.content || '', streaming: false }]
            }
            // Backend sent done without any chunks (or chunks not applied yet): add reply in one go
            if (finalContent) {
              return [...prev, { role: 'assistant', content: finalContent, streaming: false }]
            }
            return prev
          })
          setIsLoading(false)
        } else if (type === 'error') {
          const errMsg = data.message || 'Unknown error'
          console.error('[Chat] Backend error:', errMsg)
          setError(errMsg)
          setIsLoading(false)
          setMessages((prev) => [
            ...prev,
            { role: 'assistant', content: `Error: ${errMsg}`, error: true },
          ])
        }
      } catch (err) {
        console.error('[Chat] Parse/handler error:', err)
        setError(err.message)
        setIsLoading(false)
      }
    }
  }, [])

  useEffect(() => {
    connect()
    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current)
      wsRef.current?.close()
    }
  }, [connect])

  const sendMessage = useCallback((text) => {
    const trimmed = (text || '').trim()
    if (!trimmed) return
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.error('[Chat] Cannot send: WebSocket not open', wsRef.current?.readyState)
      setError('Not connected. Reconnecting…')
      return
    }
    setError(null)
    pendingContentRef.current = ''
    const userMsg = { role: 'user', content: trimmed }
    const history = messagesRef.current
      .filter((m) => m.role === 'user' || m.role === 'assistant')
      .map((m) => ({ role: m.role, content: m.content || '' }))
      .slice(-20)
    setMessages((prev) => [...prev, userMsg])
    setIsLoading(true)
    const payload = { message: trimmed, history }
    const { clusterId: cid, clusterName: cname } = clusterContextRef.current
    if (cid != null || cname) {
      payload.cluster_id = cid
      payload.cluster_name = cname
    }
    try {
      wsRef.current.send(JSON.stringify(payload))
    } catch (err) {
      console.error('[Chat] Send failed:', err)
      setError(err.message)
      setIsLoading(false)
    }
  }, [])

  const clearMessages = useCallback(() => {
    setMessages([])
    setError(null)
    pendingContentRef.current = ''
  }, [])

  return {
    messages,
    sendMessage,
    isLoading,
    error,
    connected,
    clearMessages,
  }
}
