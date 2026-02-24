import React from 'react'

/**
 * Single message bubble (user or assistant) with optional tool calls.
 */
export default function ChatMessage({ message }) {
  const isUser = message.role === 'user'
  const isError = message.error

  return (
    <div
      className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'} animate-slide-in`}
    >
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 ${
          isUser
            ? 'bg-accent/15 text-white'
            : isError
              ? 'bg-accent-red/15 text-accent-red border border-accent-red/30'
              : 'bg-surface2 text-white border border-border'
        }`}
      >
        <div className="font-mono text-sm whitespace-pre-wrap break-words">
          {message.content || (message.streaming ? '\u200b' : '')}
          {message.streaming && (
            <span className="inline-block w-2 h-4 ml-0.5 bg-accent animate-pulse" />
          )}
        </div>
        {message.toolCalls?.length > 0 && (
          <div className="mt-2 pt-2 border-t border-border/50">
            <div className="text-xs font-mono text-muted uppercase tracking-wider mb-1">
              Used tools
            </div>
            <ul className="space-y-1">
              {message.toolCalls.map((tc, i) => (
                <li key={i} className="text-xs text-muted">
                  <span className="text-accent">{tc.name}</span>
                  {tc.result && (
                    <span className="block mt-0.5 text-muted/80 truncate max-w-md" title={tc.result}>
                      {tc.result}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}
