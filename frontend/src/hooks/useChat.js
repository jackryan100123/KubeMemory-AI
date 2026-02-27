/**
 * useChat: session-based chat with SSE streaming and tool-call transparency.
 * Use with the REST/SSE chat backend (POST /api/chat/sessions/{id}/message/).
 * onStreamDone(sessionId): optional callback when a response finishes (e.g. to refetch session list).
 */
import { useState, useCallback, useRef } from 'react'
import { createSession, getSession, sendMessage } from '../api/chat'

export function useChat(namespace = 'all', { onStreamDone } = {}) {
  const [sessionId, setSessionId] = useState(null)
  const [messages, setMessages] = useState([])
  const [streaming, setStreaming] = useState(false)
  const [toolCalls, setToolCalls] = useState([])
  const streamingContent = useRef('')
  const onDoneRef = useRef(onStreamDone)
  onDoneRef.current = onStreamDone

  const startSession = useCallback(async () => {
    const session = await createSession(namespace)
    setSessionId(session.id)
    setMessages([])
    setToolCalls([])
    return session
  }, [namespace])

  const loadSession = useCallback(async (id) => {
    try {
      const session = await getSession(id)
      setSessionId(id)
      setMessages(
        (session.messages || []).map((m) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          tool_name: m.tool_name,
          tool_input: m.tool_input,
          tool_output: m.tool_output,
          tool_success: m.tool_success,
          latency_ms: m.latency_ms,
          created_at: m.created_at,
          toolsUsed: [],
        }))
      )
      setToolCalls([])
      return session
    } catch (err) {
      setSessionId(null)
      setMessages([])
      setToolCalls([])
      throw err
    }
  }, [])

  const clearSession = useCallback(() => {
    setSessionId(null)
    setMessages([])
    setToolCalls([])
  }, [])

  const sendUserMessage = useCallback(
    async (text) => {
      if (!sessionId || streaming) return

      const userMsg = { role: 'user', content: text, id: `u-${Date.now()}` }
      setMessages((prev) => [...prev, userMsg])
      setStreaming(true)
      setToolCalls([])
      streamingContent.current = ''

      const assistantMsg = {
        role: 'assistant',
        content: '',
        id: `a-${Date.now()}`,
        streaming: true,
        toolCalls: [],
      }
      setMessages((prev) => [...prev, assistantMsg])

      try {
        await sendMessage(sessionId, text, (event) => {
        if (event.type === 'token') {
          streamingContent.current += event.content || ''
          setMessages((prev) => {
            const updated = [...prev]
            const last = updated[updated.length - 1]
            if (last && last.role === 'assistant') {
              updated[updated.length - 1] = {
                ...last,
                content: streamingContent.current,
              }
            }
            return updated
          })
        } else if (event.type === 'tool_call') {
          setToolCalls((prev) => [
            ...prev,
            {
              tool: event.tool,
              description: event.description,
              input: event.input,
              status: 'running',
              id: Date.now() + prev.length,
            },
          ])
        } else if (event.type === 'tool_result') {
          setToolCalls((prev) =>
            prev.map((tc) =>
              tc.tool === event.tool
                ? {
                    ...tc,
                    status: event.success ? 'done' : 'error',
                    output: event.output,
                  }
                : tc
            )
          )
        } else if (event.type === 'done') {
          setMessages((prev) => {
            const updated = [...prev]
            const last = updated[updated.length - 1]
            if (last && last.role === 'assistant') {
              updated[updated.length - 1] = {
                ...last,
                streaming: false,
                id: event.message_id,
                latency_ms: event.latency_ms,
                toolsUsed: event.tools_used || [],
              }
            }
            return updated
          })
          setStreaming(false)
          const sid = sessionId
          if (sid && onDoneRef.current) onDoneRef.current(sid)
        } else if (event.type === 'error') {
          setStreaming(false)
          setMessages((prev) => {
            const copy = [...prev]
            const last = copy[copy.length - 1]
            if (last && last.role === 'assistant' && last.streaming) {
              copy[copy.length - 1] = {
                role: 'assistant',
                content: `Error: ${event.message}`,
                error: true,
                id: `e-${Date.now()}`,
              }
            } else {
              copy.push({
                role: 'assistant',
                content: `Error: ${event.message}`,
                error: true,
                id: `e-${Date.now()}`,
              })
            }
            return copy
          })
        }
      })
      } catch (err) {
        setStreaming(false)
        setMessages((prev) => {
          const copy = [...prev]
          const last = copy[copy.length - 1]
          if (last && last.role === 'assistant' && last.streaming) {
            copy[copy.length - 1] = {
              role: 'assistant',
              content: `Error: ${err.message || 'Request failed'}`,
              error: true,
              id: `e-${Date.now()}`,
            }
          } else {
            copy.push({
              role: 'assistant',
              content: `Error: ${err.message || 'Request failed'}`,
              error: true,
              id: `e-${Date.now()}`,
            })
          }
          return copy
        })
      }
    },
    [sessionId, streaming]
  )

  return {
    sessionId,
    messages,
    streaming,
    toolCalls,
    startSession,
    loadSession,
    clearSession,
    sendUserMessage,
  }
}
