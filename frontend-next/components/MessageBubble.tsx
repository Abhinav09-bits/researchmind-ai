'use client'
import { useState } from 'react'
import type { ChatMessage } from '@/lib/types'
import { formatAnswer, confidenceBadgeClass, faithBadgeClass, faithLabel } from '@/lib/utils'

export function TypingBubble() {
  return (
    <div className="fade-up flex gap-3">
      <div className="w-7 h-7 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex-shrink-0 flex items-center justify-center text-white text-xs font-bold mt-1">R</div>
      <div className="bg-[#1a1d27] rounded-2xl rounded-tl-sm px-4 py-3 flex items-center gap-1">
        <span className="dot w-1.5 h-1.5 bg-slate-400 rounded-full inline-block" />
        <span className="dot w-1.5 h-1.5 bg-slate-400 rounded-full inline-block" />
        <span className="dot w-1.5 h-1.5 bg-slate-400 rounded-full inline-block" />
      </div>
    </div>
  )
}

export function SystemBubble({ content }: { content: string }) {
  return (
    <div className="fade-up flex justify-center">
      <div className="bg-[#1a1d27] border border-[#2a2d3a] rounded-full px-4 py-1.5 text-xs text-slate-400">{content}</div>
    </div>
  )
}

export function ErrorBubble({ content }: { content: string }) {
  return (
    <div className="fade-up flex gap-3">
      <div className="w-7 h-7 rounded-full bg-red-500 flex-shrink-0 flex items-center justify-center text-white text-xs font-bold">!</div>
      <div className="bg-red-900/30 border border-red-800/50 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-red-300">{content}</div>
    </div>
  )
}

export default function MessageBubble({ msg }: { msg: ChatMessage }) {
  const [expandedSource, setExpandedSource] = useState<string | null>(null)

  if (msg.role === 'user') {
    return (
      <div className="fade-up flex justify-end">
        <div className="max-w-xl bg-indigo-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 text-sm leading-relaxed">
          {msg.content}
        </div>
      </div>
    )
  }

  if (msg.role === 'system') return <SystemBubble content={msg.content} />

  const data = msg.data
  return (
    <div className="fade-up flex gap-3">
      <div className="w-7 h-7 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex-shrink-0 flex items-center justify-center text-white text-xs font-bold mt-1">R</div>
      <div className="flex-1 max-w-3xl">
        <div
          className="bg-[#1a1d27] rounded-2xl rounded-tl-sm px-4 py-3 text-sm leading-relaxed text-slate-200"
          dangerouslySetInnerHTML={{ __html: formatAnswer(msg.content) }}
        />

        {data && data.sources.length > 0 && (
          <div className="mt-3 space-y-2">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider ml-1">Sources</p>
            {data.sources.map(s => (
              <div key={s.chunk_id} className="border-l-2 border-indigo-500 bg-[#1a1d27] rounded-lg overflow-hidden">
                <button
                  onClick={() => setExpandedSource(expandedSource === s.chunk_id ? null : s.chunk_id)}
                  className="w-full px-3 py-2 flex items-center justify-between hover:bg-[#1e2130] transition-colors text-left">
                  <span className="text-xs font-medium text-indigo-400 truncate">📄 {s.source_file} · Page {s.page_number ?? '?'}</span>
                  <span className="text-xs text-slate-500 ml-2 shrink-0">Score: {(s.similarity_score * 100).toFixed(0)}%</span>
                </button>
                {expandedSource === s.chunk_id && (
                  <div className="px-3 py-2 text-xs text-slate-400 border-t border-[#2a2d3a] leading-relaxed max-h-32 overflow-y-auto">
                    {s.content}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {data && (
          <div className="flex flex-wrap gap-1.5 mt-2 ml-1 items-center">
            <span className="text-xs text-slate-600">
              {data.total_sources_found} sources · {data.processing_time_ms.toFixed(0)}ms ·{' '}
              <span className="text-indigo-500/70">{data.search_mode}</span>
            </span>
            {data.reranking_applied && (
              <span className="badge-rerank px-2 py-0.5 rounded-full text-xs">✦ reranked</span>
            )}
            {data.confidence && (
              <span className={`${confidenceBadgeClass(data.confidence.level)} px-2 py-0.5 rounded-full text-xs`}>
                {data.confidence.label}
              </span>
            )}
            {data.faithfulness?.checked && (
              <span
                className={`${faithBadgeClass(data.faithfulness.verdict)} px-2 py-0.5 rounded-full text-xs cursor-help`}
                title={data.faithfulness.explanation}>
                {faithLabel(data.faithfulness.verdict)}
              </span>
            )}
            {data.preprocessed_question && data.preprocessed_question !== data.question && (
              <span className="text-xs text-slate-500">🔍 &quot;{data.preprocessed_question}&quot;</span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
