import React from 'react'
import { formatDistanceToNow } from 'date-fns'

/**
 * Left panel: New Chat, list of past sessions (title, namespace, time ago).
 * Click session -> loadSession(id). Optional delete on hover/action.
 */
export default function SessionSidebar({
  sessions = [],
  currentSessionId,
  onNewSession,
  onSelectSession,
  onDeleteSession,
  onClearAllSessions,
  loading,
}) {
  return (
    <div className="w-64 shrink-0 border-r border-border bg-surface/50 flex flex-col">
      <div className="p-3 border-b border-border space-y-2">
        <button
          type="button"
          onClick={onNewSession}
          disabled={loading}
          className="w-full py-2.5 px-3 rounded-xl bg-accent text-bg font-mono text-sm font-medium hover:bg-accent/90 disabled:opacity-50 transition-colors"
        >
          + New Chat
        </button>
        {onClearAllSessions && sessions.length > 0 && (
          <button
            type="button"
            onClick={onClearAllSessions}
            disabled={loading}
            className="w-full py-1.5 px-3 rounded-lg border border-border bg-surface2 font-mono text-xs text-muted hover:text-accent-red hover:border-accent-red/50 disabled:opacity-50 transition-colors"
          >
            Clear all sessions
          </button>
        )}
      </div>
      <div className="flex-1 overflow-y-auto p-2">
        {sessions.length === 0 && !loading && (
          <p className="text-muted font-mono text-xs px-2 py-4">
            No sessions yet. Start a new chat.
          </p>
        )}
        <ul className="space-y-1">
          {sessions.map((s) => {
            const isActive = currentSessionId === s.id
            const hasRealTitle = s.title && s.title.trim() && s.title !== 'New chat'
            const preview = (s.last_message?.content || '').trim().slice(0, 45)
            const fallbackLabel = s.updated_at
              ? `New chat • ${formatDistanceToNow(new Date(s.updated_at), { addSuffix: true })}`
              : 'New chat'
            const title = hasRealTitle ? s.title : (preview ? `${preview}${(s.last_message?.content || '').length > 45 ? '…' : ''}` : fallbackLabel)
            return (
              <li key={s.id} className="group relative">
                <button
                  type="button"
                  onClick={() => onSelectSession(s.id)}
                  className={`w-full text-left px-3 py-2.5 rounded-xl font-mono text-sm transition-colors ${
                    isActive
                      ? 'bg-accent/20 text-white border border-accent/50'
                      : 'text-white hover:bg-surface2 border border-transparent'
                  }`}
                >
                  <span className="block truncate pr-6">{title}</span>
                  <span className="flex items-center gap-1.5 mt-1 text-xs text-muted">
                    <span className="px-1.5 py-0.5 rounded bg-surface border border-border">
                      {s.namespace || 'all'}
                    </span>
                    {s.updated_at && (
                      <span>
                        {formatDistanceToNow(new Date(s.updated_at), { addSuffix: true })}
                      </span>
                    )}
                  </span>
                </button>
                {onDeleteSession && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      onDeleteSession(s.id)
                    }}
                    className="absolute right-2 top-2.5 opacity-0 group-hover:opacity-100 p-1 rounded text-muted hover:text-accent-red transition-all"
                    title="Delete session"
                  >
                    ✕
                  </button>
                )}
              </li>
            )
          })}
        </ul>
      </div>
    </div>
  )
}
