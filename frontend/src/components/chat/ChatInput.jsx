import React, { useState, useRef, useEffect } from 'react'

/**
 * Message input with slash-command popup, multi-line, Enter to send / Shift+Enter newline.
 * parseSlashCommand maps /analyze pod ns -> natural language for the engine.
 */
export function parseSlashCommand(text) {
  const match = text.match(/^\/(\w+)\s*(.*)$/)
  if (!match) return null
  const [, command, args] = match
  const parts = (args || '').trim().split(/\s+/).filter(Boolean)
  const map = {
    analyze: parts.length >= 2
      ? `Why is ${parts[0]} pod crashing in ${parts[1]} namespace?`
      : parts.length === 1
        ? `Why is ${parts[0]} pod crashing?`
        : null,
    history: parts.length >= 2
      ? `Show me the full incident timeline for ${parts[0]} in ${parts[1]}`
      : parts.length === 1
        ? `Show me the incident timeline for ${parts[0]}`
        : null,
    blast: parts.length >= 2
      ? `What is the blast radius of ${parts[0]} in ${parts[1]}?`
      : parts.length === 1
        ? `What is the blast radius of ${parts[0]}?`
        : null,
    risk: parts.length >= 2
      ? `Is it safe to deploy ${parts[0]} to ${parts[1]} right now?`
      : parts.length === 1
        ? `Is it safe to deploy ${parts[0]} right now?`
        : null,
    patterns: `What are the most recurring patterns in ${parts[0] || 'the cluster'}?`,
    search: parts.length ? parts.join(' ') : null,
    clear: null,
    new: null,
  }
  return map[command] !== undefined ? map[command] : null
}

export default function ChatInput({
  onSend,
  disabled,
  placeholder = 'Ask about incidents, root causes, or type / for commands...',
  commands = [],
  onSlashClear,
  onSlashNew,
}) {
  const [value, setValue] = useState('')
  const [showSlashPopup, setShowSlashPopup] = useState(false)
  const [slashFilter, setSlashFilter] = useState('')
  const textareaRef = useRef(null)
  const popupRef = useRef(null)

  const send = (textToSend) => {
    const trimmed = (textToSend != null ? textToSend : value).trim()
    if (!trimmed || disabled) return
    const parsed = parseSlashCommand(trimmed)
    if (trimmed.startsWith('/clear')) {
      onSlashClear?.()
      setValue('')
      return
    }
    if (trimmed.startsWith('/new')) {
      onSlashNew?.()
      setValue('')
      return
    }
    const toSend = parsed !== null && parsed !== undefined ? parsed : trimmed
    onSend(toSend)
    setValue('')
    setShowSlashPopup(false)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  useEffect(() => {
    const v = value
    if (v === '/' || (v.startsWith('/') && !v.includes(' '))) {
      setShowSlashPopup(true)
      setSlashFilter(v.slice(1).toLowerCase())
    } else {
      setShowSlashPopup(false)
    }
  }, [value])

  useEffect(() => {
    const el = textareaRef.current
    if (el) {
      el.style.height = 'auto'
      el.style.height = `${Math.min(el.scrollHeight, 160)}px`
    }
  }, [value])

  const filteredCommands =
    commands.length > 0
      ? commands.filter(
          (c) =>
            c.command &&
            c.command.slice(1).toLowerCase().startsWith(slashFilter)
        )
      : [
          { command: '/analyze', args: '<pod> <namespace>', description: 'Deep analysis of a pod' },
          { command: '/history', args: '<pod> <namespace>', description: 'Full incident timeline' },
          { command: '/blast', args: '<pod> <namespace>', description: 'Blast radius' },
          { command: '/risk', args: '<service> <namespace>', description: 'Pre-deploy risk check' },
          { command: '/patterns', args: '[namespace]', description: 'Recurring cluster patterns' },
          { command: '/search', args: '<query>', description: 'Semantic search' },
          { command: '/clear', args: '', description: 'Clear current session' },
          { command: '/new', args: '', description: 'New session' },
        ].filter((c) => c.command.slice(1).toLowerCase().startsWith(slashFilter))

  return (
    <div className="relative">
      {showSlashPopup && (
        <div
          ref={popupRef}
          className="absolute bottom-full left-0 right-0 mb-1 rounded-xl border border-border bg-surface2 shadow-lg max-h-64 overflow-y-auto z-10"
        >
          <div className="p-2 font-mono text-xs text-muted border-b border-border">
            Slash commands
          </div>
          <ul className="p-1">
            {filteredCommands.map((c, i) => (
              <li key={i}>
                <button
                  type="button"
                  onClick={() => {
                    setValue(c.command + (c.args ? ' ' : ''))
                    setShowSlashPopup(false)
                  }}
                  className="w-full text-left px-3 py-2 rounded-lg hover:bg-surface text-sm text-white font-mono flex items-center justify-between gap-2"
                >
                  <span className="text-accent">{c.command}</span>
                  <span className="text-muted truncate">
                    {c.args} — {c.description}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
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
          onClick={() => send()}
          disabled={disabled || !value.trim()}
          className="shrink-0 px-4 py-2.5 rounded-lg bg-accent text-bg font-mono text-sm font-medium hover:bg-accent/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Send
        </button>
      </div>
      {value.length > 200 && (
        <p className="text-xs text-muted font-mono mt-1">{value.length} chars</p>
      )}
    </div>
  )
}
