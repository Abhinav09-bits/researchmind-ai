'use client'
import { useState, useEffect } from 'react'
import Sidebar from '@/components/Sidebar'
import { getAnalytics } from '@/lib/api'
import type { AnalyticsStats, IndexedSource } from '@/lib/types'

export default function AnalyticsPage() {
  const [sources, setSources] = useState<IndexedSource[]>([])
  const [stats, setStats] = useState<AnalyticsStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getAnalytics().then(s => { setStats(s); setLoading(false) }).catch(() => setLoading(false))
  }, [])

  const card = (value: string | number, label: string) => (
    <div className="bg-[#1a1d27] rounded-xl p-4 text-center">
      <p className="text-2xl font-bold text-white">{value}</p>
      <p className="text-xs text-slate-500 mt-1">{label}</p>
    </div>
  )

  return (
    <div className="flex h-full overflow-hidden" style={{ background: 'var(--bg-base)' }}>
      <Sidebar sources={sources} onSourceAdded={s => setSources(p => [...p, s])} />
      <main className="flex-1 overflow-y-auto p-8">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-2xl font-bold text-white mb-1">📊 Analytics</h1>
          <p className="text-sm text-slate-400 mb-8">Query performance, confidence distribution, and faithfulness metrics</p>

          {loading && <p className="text-slate-500">Loading...</p>}
          {!loading && !stats && <p className="text-slate-500">No analytics data yet. Ask some questions first.</p>}
          {stats && (
            <div className="space-y-8">
              {/* Summary cards */}
              <div className="grid grid-cols-3 gap-4">
                {card(stats.total_queries, 'Total queries')}
                {card(`${stats.avg_processing_time_ms.toFixed(0)}ms`, 'Avg response time')}
                {card(stats.avg_sources_found.toFixed(1), 'Avg sources found')}
              </div>

              {/* Confidence */}
              <div className="bg-[#13161f] border border-[#1e2130] rounded-xl p-6">
                <h2 className="text-sm font-semibold text-white mb-4">Confidence Distribution</h2>
                <div className="flex gap-4">
                  {[
                    { key: 'high', label: '🟢 High', cls: 'badge-high' },
                    { key: 'medium', label: '🟡 Medium', cls: 'badge-medium' },
                    { key: 'low', label: '🔴 Low', cls: 'badge-low' },
                  ].map(({ key, label, cls }) => (
                    <div key={key} className="flex-1 bg-[#1a1d27] rounded-lg p-4 text-center">
                      <p className={`text-xl font-bold ${cls.includes('high') ? 'text-emerald-400' : cls.includes('medium') ? 'text-yellow-400' : 'text-red-400'}`}>
                        {stats.confidence_distribution[key as 'high' | 'medium' | 'low']}
                      </p>
                      <span className={`${cls} px-2 py-0.5 rounded-full text-xs mt-1 inline-block`}>{label}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Faithfulness */}
              <div className="bg-[#13161f] border border-[#1e2130] rounded-xl p-6">
                <h2 className="text-sm font-semibold text-white mb-4">Faithfulness Distribution</h2>
                <div className="flex gap-4">
                  {[
                    { key: 'FAITHFUL', label: '✓ Faithful', cls: 'text-emerald-400' },
                    { key: 'PARTIALLY_FAITHFUL', label: '~ Partial', cls: 'text-yellow-400' },
                    { key: 'NOT_FAITHFUL', label: '✗ Hallucination', cls: 'text-red-400' },
                  ].map(({ key, label, cls }) => (
                    <div key={key} className="flex-1 bg-[#1a1d27] rounded-lg p-4 text-center">
                      <p className={`text-xl font-bold ${cls}`}>
                        {stats.faithfulness_distribution[key as keyof typeof stats.faithfulness_distribution]}
                      </p>
                      <p className="text-xs text-slate-500 mt-1">{label}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Search modes */}
              <div className="bg-[#13161f] border border-[#1e2130] rounded-xl p-6">
                <h2 className="text-sm font-semibold text-white mb-4">Search Mode Usage</h2>
                <div className="flex gap-4">
                  {(['hybrid', 'semantic', 'keyword'] as const).map(m => (
                    <div key={m} className="flex-1 bg-[#1a1d27] rounded-lg p-4 text-center">
                      <p className="text-xl font-bold text-indigo-400">{stats.search_mode_distribution[m]}</p>
                      <p className="text-xs text-slate-500 mt-1 capitalize">{m}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Recent queries */}
              {stats.recent_queries.length > 0 && (
                <div className="bg-[#13161f] border border-[#1e2130] rounded-xl p-6">
                  <h2 className="text-sm font-semibold text-white mb-4">Recent Queries</h2>
                  <div className="space-y-2">
                    {stats.recent_queries.map((q, i) => (
                      <div key={i} className="flex items-center gap-3 bg-[#1a1d27] rounded-lg px-3 py-2">
                        <p className="flex-1 text-xs text-white truncate">{q.query}</p>
                        <span className="text-xs text-slate-500">{q.confidence}</span>
                        <span className="text-xs text-slate-500">{q.time_ms.toFixed(0)}ms</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
