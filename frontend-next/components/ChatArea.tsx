'use client'
import { useState, useRef, useEffect } from 'react'
import { sendQuery } from '@/lib/api'
import type { ChatMessage, SearchMode } from '@/lib/types'
import MessageBubble, { TypingBubble, ErrorBubble } from './MessageBubble'

export default function ChatArea() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [mode, setMode] = useState<SearchMode>('hybrid')
  const [rerank, setRerank] = useState(true)
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  function autoResize() {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 120) + 'px'
  }

  async function handleSend() {
    const q = input.trim()
    if (!q || loading) return
    setInput('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'

    const userMsg: ChatMessage = { id: Date.now().toString(), role: 'user', content: q }
    setMessages(prev => [...prev, userMsg])
    setLoading(true)

    try {
      const data = await sendQuery(q, mode, rerank)
      const aiMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.answer,
        data,
      }
      setMessages(prev => [...prev, aiMsg])
    } catch (e: any) {
      const errMsg: ChatMessage = { id: (Date.now() + 1).toString(), role: 'system', content: e.message }
      setMessages(prev => [...prev, errMsg])
    } finally {
      setLoading(false)
    }
  }

  const modeButtons: { key: SearchMode; label: string }[] = [
    { key: 'hybrid', label: '⚡ Hybrid' },
    { key: 'semantic', label: '🧠 Semantic' },
    { key: 'keyword', label: '🔑 Keyword' },
  ]

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Topbar */}
      <div className="h-14 border-b border-[#1e2130] bg-[#13161f] flex items-center px-6 justify-between shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-sm text-slate-400">Connected to Qdrant Cloud</span>
        </div>
        <button onClick={() => setMessages([])} className="text-xs text-slate-500 hover:text-slate-300 transition-colors">Clear chat</button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 && (
          <div className="flex justify-center mt-16">
            <div className="text-center max-w-md">
              <div className="text-5xl mb-4">🧠</div>
              <h2 className="text-xl font-semibold text-white mb-2">Welcome to <span className="grad">ResearchMind AI</span></h2>
              <p className="text-sm text-slate-400">Upload a PDF or index a web page / GitHub repo, then ask anything about it.</p>
            </div>
          </div>
        )}
        {messages.map(msg =>
          msg.role === 'system' && !msg.data
            ? <ErrorBubble key={msg.id} content={msg.content} />
            : <MessageBubble key={msg.id} msg={msg} />
        )}
        {loading && <TypingBubble />}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t border-[#1e2130] bg-[#13161f] p-4 shrink-0">
        <div className="flex justify-center items-center gap-2 mb-3 flex-wrap">
          <div className="flex gap-1">
            {modeButtons.map(b => (
              <button key={b.key} onClick={() => setMode(b.key)}
                className={`px-3 py-1 text-xs rounded-full border transition-colors ${mode === b.key
                  ? 'bg-indigo-500/15 text-indigo-400 border-indigo-500'
                  : 'bg-[#1a1d27] text-slate-500 border-[#2a2d3a] hover:text-slate-300'}`}>
                {b.label}
              </button>
            ))}
          </div>
          <div className="w-px h-4 bg-[#2a2d3a]" />
          <button onClick={() => setRerank(r => !r)}
            className={`px-3 py-1 text-xs rounded-full border transition-colors ${rerank
              ? 'bg-emerald-500/12 text-emerald-400 border-emerald-500'
              : 'bg-[#1a1d27] text-slate-500 border-[#2a2d3a]'}`}>
            ✦ Rerank {rerank ? 'ON' : 'OFF'}
          </button>
        </div>

        <div className="flex gap-3 items-end max-w-4xl mx-auto">
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={e => { setInput(e.target.value); autoResize() }}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() } }}
            placeholder="Ask a question about your documents..."
            className="flex-1 bg-[#1a1d27] border border-[#2a2d3a] focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 resize-none outline-none transition-colors"
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="bg-gradient-to-r from-indigo-600 to-purple-600 hover:opacity-90 disabled:opacity-50 text-white rounded-xl px-5 py-3 text-sm font-medium flex items-center gap-2 whitespace-nowrap transition-opacity">
            Ask AI →
          </button>
        </div>
        <p className="text-center text-xs text-slate-600 mt-2">
          <kbd className="bg-[#1e2130] px-1.5 py-0.5 rounded text-slate-400">Enter</kbd> to send ·{' '}
          <kbd className="bg-[#1e2130] px-1.5 py-0.5 rounded text-slate-400">Shift+Enter</kbd> for new line
        </p>
      </div>
    </div>
  )
}
