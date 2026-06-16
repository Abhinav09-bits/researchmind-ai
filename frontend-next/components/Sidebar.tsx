'use client'
import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { uploadPdf, ingestWeb, ingestGitHub, ingestYouTube } from '@/lib/api'
import type { IndexedSource } from '@/lib/types'
import { SOURCE_ICONS } from '@/lib/utils'

interface Props {
  sources: IndexedSource[]
  onSourceAdded: (src: IndexedSource) => void
}

type Tab = 'pdf' | 'web' | 'github' | 'youtube'

export default function Sidebar({ sources, onSourceAdded }: Props) {
  const pathname = usePathname()
  const [tab, setTab] = useState<Tab>('pdf')
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState<{ icon: string; name: string; msg: string } | null>(null)
  const [webUrl, setWebUrl] = useState('')
  const [ghRepo, setGhRepo] = useState('')
  const [ghBranch, setGhBranch] = useState('')
  const [ghToken, setGhToken] = useState('')
  const [ytUrl, setYtUrl] = useState('')

  const totalChunks = sources.reduce((s, d) => s + d.chunks, 0)

  async function handlePdf(file: File) {
    setLoading(true)
    setStatus({ icon: '⏳', name: file.name, msg: 'Indexing...' })
    try {
      const r = await uploadPdf(file)
      setStatus({ icon: '✅', name: file.name, msg: `${r.total_chunks} chunks` })
      onSourceAdded({ id: r.document_id, name: file.name, type: 'pdf', chunks: r.total_chunks })
    } catch (e: any) {
      setStatus({ icon: '❌', name: file.name, msg: e.message })
    } finally { setLoading(false) }
  }

  async function handleWeb() {
    if (!webUrl) return
    setLoading(true)
    setStatus({ icon: '⏳', name: webUrl, msg: 'Scraping...' })
    try {
      const r = await ingestWeb(webUrl)
      setStatus({ icon: '✅', name: webUrl, msg: `${r.total_chunks} chunks` })
      onSourceAdded({ id: r.document_id, name: webUrl, type: 'web', chunks: r.total_chunks })
      setWebUrl('')
    } catch (e: any) {
      setStatus({ icon: '❌', name: webUrl, msg: e.message })
    } finally { setLoading(false) }
  }

  async function handleGitHub() {
    if (!ghRepo) return
    const branch = ghBranch || 'main'
    setLoading(true)
    setStatus({ icon: '⏳', name: ghRepo, msg: `@${branch}...` })
    try {
      const r = await ingestGitHub(ghRepo, branch, ghToken || undefined)
      setStatus({ icon: '✅', name: ghRepo, msg: `${r.total_chunks} chunks` })
      onSourceAdded({ id: r.document_id, name: ghRepo, type: 'github', chunks: r.total_chunks })
      setGhRepo(''); setGhBranch(''); setGhToken('')
    } catch (e: any) {
      setStatus({ icon: '❌', name: ghRepo, msg: e.message })
    } finally { setLoading(false) }
  }

  async function handleYouTube() {
    if (!ytUrl) return
    setLoading(true)
    setStatus({ icon: '⏳', name: ytUrl, msg: 'Fetching transcript...' })
    try {
      const r = await ingestYouTube(ytUrl)
      setStatus({ icon: '✅', name: ytUrl, msg: `${r.total_chunks} chunks` })
      onSourceAdded({ id: r.document_id, name: ytUrl, type: 'youtube', chunks: r.total_chunks })
      setYtUrl('')
    } catch (e: any) {
      setStatus({ icon: '❌', name: ytUrl, msg: e.message })
    } finally { setLoading(false) }
  }

  const inputCls = 'w-full bg-[#1a1d27] border border-[#2a2d3a] rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 mb-2'
  const tabs: Tab[] = ['pdf', 'web', 'github', 'youtube']
  const tabLabels: Record<Tab, string> = { pdf: '📄', web: '🌐', github: '🐙', youtube: '🎥' }

  return (
    <aside className="w-72 flex flex-col bg-[#13161f] border-r border-[#1e2130]">
      {/* Logo */}
      <div className="p-5 border-b border-[#1e2130]">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-sm font-bold">R</div>
          <div>
            <h1 className="font-semibold text-white text-sm">ResearchMind AI</h1>
            <p className="text-xs text-slate-500">RAG Research Assistant</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex border-b border-[#1e2130]">
        {[
          { href: '/', label: '💬 Chat' },
          { href: '/analytics', label: '📊 Analytics' },
          { href: '/resume', label: '📋 Resume' },
        ].map(({ href, label }) => (
          <Link key={href} href={href}
            className={`flex-1 text-center py-2.5 text-xs font-medium transition-colors ${pathname === href ? 'text-indigo-400 border-b-2 border-indigo-500' : 'text-slate-500 hover:text-slate-300'}`}>
            {label}
          </Link>
        ))}
      </nav>

      {/* Source tabs */}
      <div className="p-4 border-b border-[#1e2130]">
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Add Source</p>
        <div className="flex gap-1 mb-3 border-b border-[#1e2130]">
          {tabs.map(t => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-2 py-1 text-xs transition-colors border-b-2 ${tab === t ? 'text-indigo-400 border-indigo-500' : 'text-slate-500 border-transparent hover:text-slate-300'}`}>
              {tabLabels[t]}
            </button>
          ))}
        </div>

        {tab === 'pdf' && (
          <label className="block border-2 border-dashed border-[#2a2d3a] hover:border-indigo-500 rounded-xl p-4 text-center cursor-pointer transition-colors">
            <div className="text-2xl mb-1">📄</div>
            <p className="text-xs text-slate-400">Drop PDF or <span className="text-indigo-400">browse</span></p>
            <p className="text-xs text-slate-600 mt-0.5">Max 50MB</p>
            <input type="file" accept=".pdf" className="hidden" onChange={e => e.target.files?.[0] && handlePdf(e.target.files[0])} />
          </label>
        )}
        {tab === 'web' && (
          <>
            <input value={webUrl} onChange={e => setWebUrl(e.target.value)} placeholder="https://example.com/article" className={inputCls} />
            <button onClick={handleWeb} disabled={loading} className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 disabled:opacity-50 text-white rounded-lg px-3 py-2 text-xs font-medium">Index Page</button>
          </>
        )}
        {tab === 'github' && (
          <>
            <input value={ghRepo} onChange={e => setGhRepo(e.target.value)} placeholder="owner/repo-name" className={inputCls} />
            <input value={ghBranch} onChange={e => setGhBranch(e.target.value)} placeholder="Branch (default: main)" className={inputCls} />
            <input value={ghToken} onChange={e => setGhToken(e.target.value)} type="password" placeholder="GitHub token (optional)" className={inputCls} />
            <button onClick={handleGitHub} disabled={loading} className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 disabled:opacity-50 text-white rounded-lg px-3 py-2 text-xs font-medium">Index Repo</button>
          </>
        )}
        {tab === 'youtube' && (
          <>
            <input value={ytUrl} onChange={e => setYtUrl(e.target.value)} placeholder="https://youtube.com/watch?v=..." className={inputCls} />
            <button onClick={handleYouTube} disabled={loading} className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 disabled:opacity-50 text-white rounded-lg px-3 py-2 text-xs font-medium">Index Transcript</button>
          </>
        )}

        {status && (
          <div className="mt-3 flex items-center gap-2 p-2.5 rounded-lg bg-[#1a1d27]">
            <span className="text-base">{status.icon}</span>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-white truncate">{status.name}</p>
              <p className="text-xs text-slate-400">{status.msg}</p>
            </div>
          </div>
        )}
      </div>

      {/* Knowledge base list */}
      <div className="flex-1 overflow-y-auto p-4">
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Knowledge Base</p>
        {sources.length === 0
          ? <p className="text-xs text-slate-600 italic">No sources yet</p>
          : <div className="space-y-1">
              {sources.map(s => (
                <div key={s.id} className="px-3 py-2 rounded-lg hover:bg-[#1a1d27] transition-colors border-l-2 border-transparent hover:border-indigo-500">
                  <p className="text-xs font-medium text-white truncate">{SOURCE_ICONS[s.type]} {s.name}</p>
                  <p className="text-xs text-slate-500">{s.chunks} chunks · {s.type}</p>
                </div>
              ))}
            </div>
        }
      </div>

      {/* Footer stats */}
      <div className="p-4 border-t border-[#1e2130]">
        <div className="flex justify-between text-xs text-slate-500">
          <span>Sources: <span className="text-slate-300">{sources.length}</span></span>
          <span>Chunks: <span className="text-slate-300">{totalChunks}</span></span>
        </div>
      </div>
    </aside>
  )
}
