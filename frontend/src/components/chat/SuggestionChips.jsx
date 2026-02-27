import React from 'react'

/**
 * Shown when there are no messages. Clicking a chip fills the input and can auto-send.
 * Props: suggestions (from API), onSelect(text) — called with suggestion text (caller can send).
 */
export default function SuggestionChips({ suggestions = [], onSelect }) {
  if (!suggestions.length) return null

  return (
    <div className="rounded-2xl border border-border bg-surface2/50 p-6">
      <p className="text-muted font-mono text-sm mb-4">
        🧠 What would you like to know?
      </p>
      <div className="flex flex-wrap gap-2">
        {suggestions.map((s, i) => (
          <button
            key={i}
            type="button"
            onClick={() => onSelect(s.text)}
            className="px-4 py-2.5 rounded-xl border border-border bg-surface hover:bg-surface2 hover:border-accent/30 text-left font-mono text-sm text-white transition-colors"
          >
            <span className="mr-1.5">{s.icon || '•'}</span>
            {s.text}
          </button>
        ))}
      </div>
    </div>
  )
}
