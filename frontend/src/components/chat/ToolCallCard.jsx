import React from 'react'

/**
 * Inline card for a tool call: running (pulsing), done (green), error (red).
 * Shows tool name, description, input summary, and output when done.
 */
export default function ToolCallCard({ toolCall }) {
  const { tool, description, input, status, output } = toolCall
  const isRunning = status === 'running'
  const isDone = status === 'done'
  const isError = status === 'error'

  return (
    <div
      className={`rounded-xl border p-3 text-sm font-mono transition-colors ${
        isRunning
          ? 'border-accent/50 bg-accent/10'
          : isError
            ? 'border-accent-red/50 bg-accent-red/10'
            : 'border-border bg-surface2'
      } ${isRunning ? 'animate-pulse' : ''}`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-accent font-medium">⚙️ {tool}</span>
        <span
          className={`text-xs uppercase flex items-center gap-1.5 ${
            isRunning
              ? 'text-accent'
              : isError
                ? 'text-accent-red'
                : 'text-emerald-400'
          }`}
        >
          {isRunning && (
            <span className="inline-block w-2 h-2 rounded-full bg-accent animate-ping" />
          )}
          {isRunning ? 'RUNNING' : isError ? '✗ ERROR' : '✓ DONE'}
        </span>
      </div>
      {description && (
        <p className="text-muted text-xs mt-1">{description}</p>
      )}
      {input && Object.keys(input).length > 0 && (
        <pre className="mt-2 text-xs text-muted overflow-x-auto">
          Input: {JSON.stringify(input)}
        </pre>
      )}
      {output != null && output !== '' && !isRunning && (
        <div
          className={`mt-2 text-xs ${
            isError ? 'text-accent-red' : 'text-muted'
          }`}
        >
          {isError ? 'Error: ' : ''}
          {typeof output === 'string' ? output.slice(0, 400) : JSON.stringify(output).slice(0, 400)}
          {(typeof output === 'string' ? output.length : JSON.stringify(output).length) > 400 && '…'}
        </div>
      )}
    </div>
  )
}
