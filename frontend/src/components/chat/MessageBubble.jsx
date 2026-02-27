import React from 'react'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

/**
 * Renders one message: user (right, dark) or assistant (left, surface, optional Markdown).
 * Streaming message shows blinking cursor. Footer: latency, tools used.
 */
export default function MessageBubble({ message }) {
  const isUser = message.role === 'user'
  const isError = message.error

  let safeHtml = ''
  if (!isUser && (message.content || '').trim()) {
    try {
      const raw = marked.parse(message.content || '', { async: false })
      safeHtml = DOMPurify.sanitize(typeof raw === 'string' ? raw : String(raw))
    } catch {
      safeHtml = ''
    }
  }

  return (
    <div className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 ${
          isUser
            ? 'bg-accent/15 text-white'
            : isError
              ? 'bg-accent-red/15 text-accent-red border border-accent-red/30'
              : 'bg-surface2 text-white border border-border'
        }`}
      >
        {isUser ? (
          <div className="font-mono text-sm whitespace-pre-wrap break-words">
            {message.content}
          </div>
        ) : (
          <>
            {safeHtml ? (
              <div
                className="prose prose-invert prose-sm max-w-none font-mono text-sm break-words"
                dangerouslySetInnerHTML={{ __html: safeHtml }}
              />
            ) : (
              <div className="font-mono text-sm whitespace-pre-wrap break-words">
                {message.content || (message.streaming ? '\u200b' : '')}
              </div>
            )}
            {message.streaming && (
              <span
                className="inline-block w-2 h-4 ml-0.5 bg-accent rounded-sm animate-pulse"
                style={{ animationDuration: '0.8s' }}
              />
            )}
          </>
        )}
        {!isUser && !message.streaming && (message.latency_ms != null || (message.toolsUsed && message.toolsUsed.length > 0)) && (
          <div className="mt-2 pt-2 border-t border-border/50 flex flex-wrap items-center gap-2 text-xs text-muted">
            {message.latency_ms != null && (
              <span>{message.latency_ms}ms</span>
            )}
            {message.toolsUsed && message.toolsUsed.length > 0 && (
              <span className="flex gap-1 flex-wrap">
                {message.toolsUsed.map((t) => (
                  <span
                    key={t}
                    className="px-1.5 py-0.5 rounded bg-surface border border-border"
                  >
                    {t}
                  </span>
                ))}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
