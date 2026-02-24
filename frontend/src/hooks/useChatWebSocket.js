import { useState, useCallback, useRef, useEffect } from 'react'

/**
 * WebSocket hook for the cluster chat assistant.
 * Connects to ws/chat/, sends messages, receives streamed chunks and tool_call events.
 * @returns {{
 *   messages: Array<{ role: 'user'|'assistant', content: string, toolCalls?: Array }>,
 *   sendMessage: (text: string) => void,
 *   isLoading: boolean,
 *   error: string | null,
 *   connected: boolean,
 *   clearMessages: () => void,
 * }}
 */
export function useChatWebSocket() {
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [connected, setConnected] = useState(false)
  const wsRef = useRef(null)
  const pendingContentRef = useRef('')
  const messagesRef = useRef([])
  messagesRef.current = messages

  const connect = useCallback(() => {
    const raw =
      import.meta.env.VITE_WS_URL ||
      (typeof window !== 'undefined'
        ? `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`
        : 'ws://localhost:8000')
    const base = typeof raw === 'string' ? raw.replace(/\/ws\/?$/, '') : raw
    const path = 'ws/chat/'
    const url = base ? `${base}${base.endsWith('/') ? '' : '/'}${path}` : `/${path}`
    wsRef.current = new WebSocket(url)

    wsRef.current.onopen = () => setConnected(true)
    wsRef.current.onclose = () => setConnected(false)
    wsRef.current.onerror = () => setError('WebSocket error')
    wsRef.current.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        const type = data.type
        if (type === 'chunk' && data.content) {
          pendingContentRef.current += data.content
          setMessages((prev) => {
            const rest = prev.slice(0, -1)
            const last = prev[prev.length - 1]
            if (last?.role === 'assistant' && last?.streaming) {
              return [...rest, { ...last, content: pendingContentRef.current, streaming: true }]
            }
            return [...rest, { role: 'assistant', content: pendingContentRef.current, streaming: true }]
          })
        } else if (type === 'tool_call') {
          setMessages((prev) => {
            const rest = prev.slice(0, -1)
            const last = prev[prev.length - 1]
            const toolCalls = [...(last?.toolCalls || []), { name: data.name, result: data.result }]
            return [...rest, { ...last, role: 'assistant', toolCalls, content: last?.content || '' }]
          })
        } else if (type === 'done') {
          pendingContentRef.current = ''
          setMessages((prev) => {
            const rest = prev.slice(0, -1)
            const last = prev[prev.length - 1]
            if (last?.role === 'assistant') {
              return [...rest, { ...last, streaming: false }]
            }
            return prev
          })
          setIsLoading(false)
        } else if (type === 'error') {
          setError(data.message || 'Unknown error')
          setIsLoading(false)
          setMessages((prev) => [
            ...prev,
            { role: 'assistant', content: `Error: ${data.message || 'Unknown'}`, error: true },
          ])
        }
      } catch (err) {
        setError(err.message)
        setIsLoading(false)
      }
    }
  }, [])

  useEffect(() => {
    connect()
    return () => {
      wsRef.current?.close()
    }
  }, [connect])

  const sendMessage = useCallback((text) => {
    const trimmed = (text || '').trim()
    if (!trimmed || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    setError(null)
    pendingContentRef.current = ''
    const userMsg = { role: 'user', content: trimmed }
    const history = messagesRef.current
      .filter((m) => m.role === 'user' || m.role === 'assistant')
      .map((m) => ({ role: m.role, content: m.content || '' }))
      .slice(-20)
    setMessages((prev) => [...prev, userMsg])
    setIsLoading(true)
    wsRef.current.send(JSON.stringify({ message: trimmed, history }))
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
