import React, { useRef, useEffect } from 'react'
import { useChatWebSocket } from '../hooks/useChatWebSocket'
import ChatMessage from '../components/chat/ChatMessage'
import ChatInput from '../components/chat/ChatInput'
import LoadingSpinner from '../components/shared/LoadingSpinner'

export default function Chat() {
  const { messages, sendMessage, isLoading, error, connected, clearMessages } = useChatWebSocket()
  const scrollRef = useRef(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  return (
    <div className="p-6 flex flex-col h-full max-h-[calc(100vh-8rem)]">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="font-mono text-xl text-white">Cluster Assistant</h1>
          <p className="text-muted text-sm mt-0.5">
            Ask about incidents, root causes, and patterns. Uses the same tools as the MCP server.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span
            className={`flex items-center gap-1.5 text-xs font-mono ${
              connected ? 'text-accent' : 'text-muted'
            }`}
          >
            <span className={`w-2 h-2 rounded-full ${connected ? 'bg-accent' : 'bg-muted'}`} />
            {connected ? 'Connected' : 'Connecting…'}
          </span>
          <button
            type="button"
            onClick={clearMessages}
            className="text-xs font-mono text-muted hover:text-white transition-colors"
          >
            Clear
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-3 px-3 py-2 rounded-lg bg-accent-red/15 text-accent-red text-sm font-mono">
          {error}
        </div>
      )}

      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto space-y-4 pb-4 min-h-0"
      >
        {messages.length === 0 && !isLoading && (
          <div className="text-center py-12 text-muted">
            <p className="font-mono text-sm">No messages yet.</p>
            <p className="font-mono text-xs mt-2 max-w-md mx-auto">
              Try: “What caused the payment service to crash?” or “Search for OOMKill incidents in production”
            </p>
          </div>
        )}
        {messages.map((msg, i) => (
          <ChatMessage key={i} message={msg} />
        ))}
        {isLoading && messages[messages.length - 1]?.role === 'user' && (
          <div className="flex justify-start">
            <div className="rounded-2xl px-4 py-3 bg-surface2 border border-border">
              <LoadingSpinner className="w-5 h-5" />
            </div>
          </div>
        )}
      </div>

      <div className="pt-3 border-t border-border">
        <ChatInput onSend={sendMessage} disabled={isLoading || !connected} />
      </div>
    </div>
  )
}
