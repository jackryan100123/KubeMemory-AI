import React, { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import {
  listSessions,
  getSuggestions,
  getCommands,
  deleteSession,
  deleteAllSessions,
} from '../api/chat'
import { useChat } from '../hooks/useChat'
import { useQuery as useClustersQuery } from '@tanstack/react-query'
import { fetchClusters } from '../api/clusters'
import SessionSidebar from '../components/chat/SessionSidebar'
import ChatWindow from '../components/chat/ChatWindow'
import ContextPanel from '../components/chat/ContextPanel'

/**
 * Full-screen chat: 3-column layout (sessions | chat | context).
 * Uses REST/SSE backend. When opening /chat with no session in URL: use most recent
 * session if any, otherwise create one (avoids creating a new session on every visit).
 */
export default function Chat() {
  const { sessionId: routeSessionId } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [contextCollapsed, setContextCollapsed] = useState(false)
  const sessionInitRef = useRef(false)
  const failedSessionIdRef = useRef(null)
  /** Prevents duplicate loadSession when effect runs multiple times (e.g. Strict Mode or rapid deps change). */
  const loadingRouteIdRef = useRef(null)

  const { data: clusters } = useClustersQuery({
    queryKey: ['clusters'],
    queryFn: fetchClusters,
  })
  const list = Array.isArray(clusters) ? clusters : clusters?.results || []
  const activeCluster = list.find((c) => c.status === 'watching' || c.status === 'connected') || list[0]
  const namespace = activeCluster?.namespace || 'all'
  const clusterName = activeCluster?.name || ''

  const {
    sessionId,
    messages,
    streaming,
    toolCalls,
    startSession,
    loadSession,
    clearSession,
    sendUserMessage,
  } = useChat(namespace, {
    onStreamDone: () => queryClient.invalidateQueries(['chat', 'sessions']),
  })

  const { data: sessions = [], isLoading: sessionsLoading } = useQuery({
    queryKey: ['chat', 'sessions'],
    queryFn: listSessions,
    refetchOnWindowFocus: false,
    staleTime: 60 * 1000,
  })

  const { data: suggestionsData } = useQuery({
    queryKey: ['chat', 'suggestions', namespace],
    queryFn: () => getSuggestions(namespace),
  })
  const suggestions = suggestionsData?.suggestions ?? []

  const { data: commandsData } = useQuery({
    queryKey: ['chat', 'commands'],
    queryFn: getCommands,
  })
  const commands = commandsData?.commands ?? []

  // Sync session with URL: load from route, or pick most recent. Never auto-create in effect.
  // Session creation only happens on explicit "+ New Chat" or when deleting the last session.
  useEffect(() => {
    if (routeSessionId) {
      if (routeSessionId === failedSessionIdRef.current) return
      // Avoid duplicate in-flight load for the same id (e.g. Strict Mode or rapid re-renders).
      if (loadingRouteIdRef.current === routeSessionId) return
      if (String(routeSessionId) !== String(sessionId)) {
        loadingRouteIdRef.current = routeSessionId
        loadSession(routeSessionId)
          .then(() => {
            loadingRouteIdRef.current = null
          })
          .catch((err) => {
            loadingRouteIdRef.current = null
            const is404 = err.response?.status === 404
            if (is404) {
              failedSessionIdRef.current = routeSessionId
              queryClient.setQueryData(['chat', 'sessions'], (prev) => {
                const list = Array.isArray(prev) ? prev : []
                return list.filter((s) => String(s.id) !== String(routeSessionId))
              })
              clearSession()
              sessionInitRef.current = false
              navigate('/chat', { replace: true })
            } else {
              // Never auto-create on load failure — would cause many sessions on refresh if backend is slow/failing.
              clearSession()
              sessionInitRef.current = false
              navigate('/chat', { replace: true })
              toast.error(err.response?.data?.error || err.message || 'Failed to load session')
            }
          })
      }
      return
    }
    failedSessionIdRef.current = null
    loadingRouteIdRef.current = null
    if (sessionsLoading) return
    const cached = queryClient.getQueryData(['chat', 'sessions'])
    const list = Array.isArray(cached) ? cached : []
    if (sessionId) {
      navigate(`/chat/${sessionId}`, { replace: true })
      return
    }
    if (sessionInitRef.current) return
    sessionInitRef.current = true
    // Only navigate to first existing session; never create here (creation is handleNewSession / delete last).
    if (list.length > 0) {
      navigate(`/chat/${list[0].id}`, { replace: true })
      loadSession(list[0].id)
    }
  }, [routeSessionId, sessionId, sessionsLoading])

  const handleNewSession = async () => {
    sessionInitRef.current = false
    const s = await startSession()
    queryClient.invalidateQueries(['chat', 'sessions'])
    if (s?.id) navigate(`/chat/${s.id}`, { replace: true })
  }

  const handleSelectSession = (id) => {
    navigate(`/chat/${id}`)
    loadSession(id)
  }

  const handleClearAllSessions = async () => {
    if (!window.confirm('Delete all chat sessions permanently? This cannot be undone.')) return
    try {
      const { deleted } = await deleteAllSessions()
      queryClient.setQueryData(['chat', 'sessions'], [])
      sessionInitRef.current = false
      clearSession()
      navigate('/chat', { replace: true })
      const s = await startSession()
      if (s?.id) navigate(`/chat/${s.id}`, { replace: true })
      queryClient.invalidateQueries(['chat', 'sessions'])
      toast.success(`Cleared ${deleted} session(s)`)
    } catch (err) {
      toast.error(err.response?.data?.error || err.message || 'Failed to clear sessions')
      queryClient.invalidateQueries(['chat', 'sessions'])
    }
  }

  const handleDeleteSession = async (id) => {
    const idStr = String(id)
    const prevList = queryClient.getQueryData(['chat', 'sessions']) || []
    const updatedList = Array.isArray(prevList) ? prevList.filter((s) => String(s.id) !== idStr) : []
    console.log('[chat] handleDeleteSession id=', idStr, 'prevCount=', prevList.length, 'afterRemoveCount=', updatedList.length)

    try {
      await deleteSession(id)
      console.log('[chat] deleteSession succeeded, updating cache and refetching')
      queryClient.setQueryData(['chat', 'sessions'], updatedList)
      if (String(sessionId) === idStr) {
        if (updatedList.length > 0) {
          const next = updatedList[0].id
          navigate(`/chat/${next}`, { replace: true })
          loadSession(next)
        } else {
          sessionInitRef.current = false
          const s = await startSession()
          if (s?.id) navigate(`/chat/${s.id}`, { replace: true })
        }
      }
      toast.success('Session deleted')
      // Do not refetch: list was coming back as 20 after each delete (race/cache). Keep optimistic cache; full reload will show server state.
    } catch (err) {
      console.log('[chat] deleteSession failed', err.response?.status, err.message)
      const is404 = err.response?.status === 404
      if (is404) {
        queryClient.setQueryData(['chat', 'sessions'], updatedList)
        if (String(sessionId) === idStr) {
          clearSession()
          sessionInitRef.current = false
          navigate('/chat', { replace: true })
        }
        toast.success('Session removed')
        return
      }
      toast.error(err.response?.data?.error || err.message || 'Failed to delete session')
      queryClient.invalidateQueries(['chat', 'sessions'])
    }
  }

  const lastAssistant = messages.filter((m) => m.role === 'assistant').pop()
  const toolsUsed = lastAssistant?.toolsUsed ?? []
  const sourceIncidentIds = [] // Could be parsed from message content or returned by API later

  return (
    <div className="flex h-full min-h-0 flex-1">
      <SessionSidebar
        sessions={sessions}
        currentSessionId={sessionId}
        onNewSession={handleNewSession}
        onSelectSession={handleSelectSession}
        onDeleteSession={handleDeleteSession}
        onClearAllSessions={handleClearAllSessions}
        loading={sessionsLoading}
      />
      <ChatWindow
        sessionId={sessionId}
        messages={messages}
        streaming={streaming}
        toolCalls={toolCalls}
        onSend={sendUserMessage}
        onNewChat={handleNewSession}
        suggestions={suggestions}
        commands={commands}
        onSuggestionSelect={(text) => sendUserMessage(text)}
        onSlashClear={handleNewSession}
        onSlashNew={handleNewSession}
      />
      <ContextPanel
        toolsUsed={toolsUsed}
        sourceIncidentIds={sourceIncidentIds}
        namespace={namespace}
        clusterName={clusterName}
        wsConnected={true}
        collapsed={contextCollapsed}
        onToggleCollapsed={() => setContextCollapsed((c) => !c)}
      />
    </div>
  )
}
