import React from 'react'

/**
 * Shown while the assistant is "thinking" (streaming but no tokens or tool calls yet).
 * Bouncing dots animation.
 */
export default function ThinkingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="rounded-2xl px-4 py-3 bg-surface2 border border-border flex items-center gap-1.5">
        <span className="text-muted font-mono text-xs uppercase tracking-wider">
          Thinking
        </span>
        <span className="flex gap-0.5">
          <span className="w-1.5 h-1.5 rounded-full bg-accent animate-bounce" style={{ animationDelay: '0ms' }} />
          <span className="w-1.5 h-1.5 rounded-full bg-accent animate-bounce" style={{ animationDelay: '150ms' }} />
          <span className="w-1.5 h-1.5 rounded-full bg-accent animate-bounce" style={{ animationDelay: '300ms' }} />
        </span>
      </div>
    </div>
  )
}
