import React, { useState, useRef, useEffect } from 'react'

/**
 * Chat input with send button. Supports Enter to send, Shift+Enter for newline.
 */
export default function ChatInput({ onSend, disabled, placeholder = 'Ask about incidents, root causes, or cluster patterns...' }) {
  const [value, setValue] = useState('')
  const textareaRef = useRef(null)

  const send = () => {
    const trimmed = value.trim()
    if (trimmed && !disabled) {
      onSend(trimmed)
      setValue('')
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  useEffect(() => {
    const el = textareaRef.current
    if (el) {
      el.style.height = 'auto'
      el.style.height = `${Math.min(el.scrollHeight, 160)}px`
    }
  }, [value])

  return (
    <div className="flex gap-2 items-end border border-border rounded-xl bg-surface2 p-2">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        rows={1}
        className="flex-1 min-h-[44px] max-h-40 resize-none bg-transparent text-white font-mono text-sm placeholder:text-muted border-none outline-none focus:ring-0"
      />
      <button
        type="button"
        onClick={send}
        disabled={disabled || !value.trim()}
        className="shrink-0 px-4 py-2.5 rounded-lg bg-accent text-bg font-mono text-sm font-medium hover:bg-accent/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        Send
      </button>
    </div>
  )
}
