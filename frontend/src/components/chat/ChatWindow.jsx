import React, { useRef, useEffect, useMemo } from 'react'
import MessageBubble from './MessageBubble'
import ToolCallCard from './ToolCallCard'
import SuggestionChips from './SuggestionChips'
import ChatInput from './ChatInput'
import ThinkingIndicator from './ThinkingIndicator'

const TOOL_DESCRIPTIONS = {
  search_incidents: 'Searching incident history...',
  analyze_pod: 'Running LangGraph 3-agent analysis...',
  get_blast_radius: 'Querying blast radius for this pod...',
  get_top_blast_radius_services: 'Finding services with largest blast radius...',
  get_patterns: 'Loading cluster patterns...',
  get_pod_timeline: 'Fetching pod incident timeline...',
  risk_check: 'Running pre-deploy risk assessment...',
  get_graph_context: 'Loading knowledge graph data...',
}

/**
 * Build a single list of display blocks (user/assistant bubbles + tool cards) so that
 * live streaming and loaded session render the same way: assistant reply, then tool cards.
 */
function buildDisplayBlocks(messages, toolCalls) {
  const blocks = []

  if (toolCalls && toolCalls.length > 0) {
    // Streaming: show only user/assistant messages, then tool cards (same as before)
    for (const msg of messages) {
      if (msg.role === 'user') blocks.push({ type: 'user', message: msg })
      if (msg.role === 'assistant') blocks.push({ type: 'assistant', message: msg })
    }
    for (const tc of toolCalls) {
      blocks.push({ type: 'tool', toolCall: tc })
    }
    return blocks
  }

  // Loaded session: convert tool_call + tool_result into tool cards; show after assistant
  let pendingTool = null
  const pendingToolBlocks = []

  for (const msg of messages) {
    if (msg.role === 'user') {
      blocks.push({ type: 'user', message: msg })
      pendingToolBlocks.length = 0
      continue
    }
    if (msg.role === 'tool_call') {
      const name = msg.tool_name || 'tool'
      pendingTool = {
        tool: name,
        description: (TOOL_DESCRIPTIONS[name] || msg.content || `Calling ${name}`),
        input: msg.tool_input || {},
        status: 'done',
        output: null,
      }
      continue
    }
    if (msg.role === 'tool_result') {
      if (pendingTool && pendingTool.tool === (msg.tool_name || pendingTool.tool)) {
        pendingTool.output = msg.tool_output ?? ''
        pendingTool.status = msg.tool_success ? 'done' : 'error'
        pendingToolBlocks.push(pendingTool)
      }
      pendingTool = null
      continue
    }
    if (msg.role === 'assistant') {
      if (pendingTool) {
        pendingTool.output = ''
        pendingTool.status = 'done'
        pendingToolBlocks.push(pendingTool)
        pendingTool = null
      }
      const toolsUsed = pendingToolBlocks.map((t) => t.tool)
      blocks.push({
        type: 'assistant',
        message: { ...msg, toolsUsed },
      })
      for (const tc of pendingToolBlocks) {
        blocks.push({ type: 'tool', toolCall: tc })
      }
      pendingToolBlocks.length = 0
    }
  }

  return blocks
}

/**
 * Main chat area: message list, tool call cards inline, suggestion chips when empty, input bar.
 * Renders the same structure for live and loaded sessions (assistant reply then tool cards).
 */
export default function ChatWindow({
  sessionId = null,
  messages = [],
  streaming,
  toolCalls = [],
  onSend,
  onNewChat,
  suggestions = [],
  commands = [],
  onSuggestionSelect,
  onSlashClear,
  onSlashNew,
}) {
  const scrollRef = useRef(null)
  const hasSession = !!sessionId

  const displayBlocks = useMemo(
    () => buildDisplayBlocks(messages, toolCalls),
    [messages, toolCalls]
  )

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, toolCalls])

  const hasMessages = messages.length > 0
  const lastMsg = hasMessages ? messages[messages.length - 1] : null
  const lastAssistant = lastMsg?.role === 'assistant'
  const lastAssistantEmpty = lastAssistant && !(lastMsg?.content || '').trim()
  const showThinking = streaming && lastAssistantEmpty && toolCalls.length === 0

  return (
    <div className="flex-1 flex flex-col min-h-0">
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto space-y-4 p-4 min-h-0"
      >
        {!hasSession && (
          <div className="rounded-2xl border border-border bg-surface2/50 p-8 text-center">
            <p className="text-muted font-mono text-sm mb-4">
              No conversation selected.
            </p>
            <p className="text-white/80 font-mono text-sm mb-6">
              Click <strong className="text-accent">+ New Chat</strong> in the sidebar to start, or select an existing conversation.
            </p>
            {onNewChat && (
              <button
                type="button"
                onClick={onNewChat}
                className="px-5 py-2.5 rounded-xl bg-accent text-bg font-mono text-sm font-medium hover:bg-accent/90 transition-colors"
              >
                Start new chat
              </button>
            )}
          </div>
        )}
        {hasSession && !hasMessages && (
          <SuggestionChips suggestions={suggestions} onSelect={onSuggestionSelect} />
        )}
        {hasSession && displayBlocks.map((block, idx) => (
          <div key={block.type === 'tool' ? `tool-${block.toolCall?.tool}-${idx}` : block.message?.id || idx}>
            {block.type === 'user' && <MessageBubble message={block.message} />}
            {block.type === 'assistant' && <MessageBubble message={block.message} />}
            {block.type === 'tool' && (
              <div className="space-y-2">
                <ToolCallCard toolCall={block.toolCall} />
              </div>
            )}
          </div>
        ))}
        {hasSession && showThinking && <ThinkingIndicator />}
      </div>
      <div className="p-4 border-t border-border">
        <ChatInput
          onSend={onSend}
          disabled={streaming || !hasSession}
          commands={commands}
          onSlashClear={onSlashClear}
          onSlashNew={onSlashNew}
        />
      </div>
    </div>
  )
}
