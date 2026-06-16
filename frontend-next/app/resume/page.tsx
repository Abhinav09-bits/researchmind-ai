'use client'
import { useState, useRef } from 'react'
import Sidebar from '@/components/Sidebar'
import { analyzeResume } from '@/lib/api'
import type { ResumeAnalysis, IndexedSource } from '@/lib/types'

export default function ResumePage() {
  const [sources, setSources] = useState<IndexedSource[]>([])
  const [resumeFile, setResumeFile] = useState<File | null>(null)
  const [jobDesc, setJobDesc] = useState('')
  const [analysis, setAnalysis] = useState<ResumeAnalysis | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState<'analysis' | 'cover' | 'email'>('analysis')
  const [copied, setCopied] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)

  async function handleAnalyze() {
    if (!resumeFile || jobDesc.trim().length < 50) {
      setError('Please upload a resume PDF and paste a job description (min 50 chars).')
      return
    }
    setError('')
    setLoading(true)
    setAnalysis(null)
    try {
      const result = await analyzeResume(resumeFile, jobDesc)
      setAnalysis(result)
      setActiveTab('analysis')
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  function copyText(text: string, key: string) {
    navigator.clipboard.writeText(text)
    setCopied(key)
    setTimeout(() => setCopied(''), 2000)
  }

  const scoreColor = !analysis ? '' : analysis.match_score >= 70 ? 'text-emerald-400' : analysis.match_score >= 40 ? 'text-yellow-400' : 'text-red-400'
  const scoreBg = !analysis ? '' : analysis.match_score >= 70 ? 'from-emerald-500 to-emerald-400' : analysis.match_score >= 40 ? 'from-yellow-500 to-yellow-400' : 'from-red-500 to-red-400'

  return (
    <div className="flex h-full overflow-hidden" style={{ background: 'var(--bg-base)' }}>
      <Sidebar sources={sources} onSourceAdded={s => setSources(p => [...p, s])} />

      <main className="flex-1 overflow-y-auto">
        <div className="h-14 border-b border-[#1e2130] bg-[#13161f] flex items-center px-6 shrink-0">
          <h1 className="text-sm font-semibold text-white">📋 Resume Analyzer</h1>
          <span className="ml-3 text-xs text-slate-500">Upload resume + paste job description → AI scores fit & writes cover letter</span>
        </div>

        <div className="p-6 max-w-7xl mx-auto">
          {/* Input row */}
          <div className="grid grid-cols-2 gap-6 mb-6">
            {/* Resume upload */}
            <div>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Resume (PDF)</p>
              <div
                onClick={() => fileRef.current?.click()}
                className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors ${resumeFile ? 'border-indigo-500 bg-indigo-500/5' : 'border-[#2a2d3a] hover:border-indigo-500'}`}>
                <div className="text-3xl mb-2">{resumeFile ? '✅' : '📄'}</div>
                {resumeFile
                  ? <p className="text-sm font-medium text-white">{resumeFile.name}</p>
                  : <p className="text-sm text-slate-400">Drop PDF or <span className="text-indigo-400">browse</span></p>}
                <p className="text-xs text-slate-600 mt-1">Max 10MB · Text-based PDF only</p>
              </div>
              <input ref={fileRef} type="file" accept=".pdf" className="hidden" onChange={e => e.target.files?.[0] && setResumeFile(e.target.files[0])} />
            </div>

            {/* Job description */}
            <div>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Job Description</p>
              <textarea
                value={jobDesc}
                onChange={e => setJobDesc(e.target.value)}
                placeholder="Paste the full job description here — requirements, responsibilities, nice-to-haves..."
                rows={7}
                className="w-full bg-[#1a1d27] border border-[#2a2d3a] focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 resize-none outline-none transition-colors"
              />
            </div>
          </div>

          {error && <p className="text-sm text-red-400 mb-4">{error}</p>}

          <button
            onClick={handleAnalyze}
            disabled={loading || !resumeFile || jobDesc.length < 50}
            className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 hover:opacity-90 disabled:opacity-50 text-white rounded-xl py-3 text-sm font-semibold mb-8 transition-opacity flex items-center justify-center gap-2">
            {loading ? (
              <>
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Analyzing resume... (takes ~15s)
              </>
            ) : '✨ Analyze & Generate Cover Letter'}
          </button>

          {/* Results */}
          {analysis && (
            <div className="space-y-6">
              {/* Score hero */}
              <div className="bg-[#13161f] border border-[#1e2130] rounded-2xl p-6 flex items-center gap-8">
                <div className="text-center shrink-0">
                  <div className={`text-6xl font-black ${scoreColor}`}>{analysis.match_score}<span className="text-2xl">%</span></div>
                  <p className="text-xs text-slate-400 mt-1">Job Match Score</p>
                  <div className="w-24 h-2 score-bar mt-2 mx-auto">
                    <div className={`score-fill bg-gradient-to-r ${scoreBg}`} style={{ width: `${analysis.match_score}%` }} />
                  </div>
                </div>
                <div className="flex-1">
                  <p className="text-sm text-slate-300 leading-relaxed">{analysis.summary}</p>
                </div>
              </div>

              {/* Keywords grid */}
              <div className="grid grid-cols-2 gap-6">
                <div className="bg-[#13161f] border border-[#1e2130] rounded-xl p-5">
                  <h3 className="text-sm font-semibold text-emerald-400 mb-3">✅ Matched Keywords ({analysis.matched_keywords.length})</h3>
                  <div className="flex flex-wrap gap-2">
                    {analysis.matched_keywords.map(k => (
                      <span key={k} className="badge-faithful px-2.5 py-1 rounded-full text-xs">{k}</span>
                    ))}
                  </div>
                </div>
                <div className="bg-[#13161f] border border-[#1e2130] rounded-xl p-5">
                  <h3 className="text-sm font-semibold text-red-400 mb-3">❌ Missing Keywords ({analysis.missing_keywords.length})</h3>
                  <div className="flex flex-wrap gap-2">
                    {analysis.missing_keywords.map(k => (
                      <span key={k} className="badge-low px-2.5 py-1 rounded-full text-xs">{k}</span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Strengths / Gaps / Recommendations */}
              <div className="grid grid-cols-3 gap-6">
                {[
                  { title: '💪 Strengths', items: analysis.strengths, color: 'text-emerald-400' },
                  { title: '⚠️ Gaps', items: analysis.gaps, color: 'text-yellow-400' },
                  { title: '🎯 Recommendations', items: analysis.recommendations, color: 'text-indigo-400' },
                ].map(({ title, items, color }) => (
                  <div key={title} className="bg-[#13161f] border border-[#1e2130] rounded-xl p-5">
                    <h3 className={`text-sm font-semibold ${color} mb-3`}>{title}</h3>
                    <ul className="space-y-2">
                      {items.map((item, i) => (
                        <li key={i} className="text-xs text-slate-400 flex gap-2">
                          <span className="shrink-0">•</span>{item}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>

              {/* Cover letter / HR email tabs */}
              <div className="bg-[#13161f] border border-[#1e2130] rounded-xl overflow-hidden">
                <div className="flex border-b border-[#1e2130]">
                  {[
                    { key: 'cover' as const, label: '📝 Cover Letter' },
                    { key: 'email' as const, label: '📧 HR Email' },
                  ].map(({ key, label }) => (
                    <button key={key} onClick={() => setActiveTab(key)}
                      className={`px-5 py-3 text-xs font-medium transition-colors ${activeTab === key ? 'text-indigo-400 border-b-2 border-indigo-500 bg-indigo-500/5' : 'text-slate-500 hover:text-slate-300'}`}>
                      {label}
                    </button>
                  ))}
                  <div className="flex-1" />
                  <button
                    onClick={() => copyText(activeTab === 'cover' ? analysis.cover_letter : analysis.hr_email, activeTab)}
                    className="px-4 py-3 text-xs text-slate-400 hover:text-white transition-colors">
                    {copied === activeTab ? '✅ Copied!' : '📋 Copy'}
                  </button>
                </div>
                <div className="p-5">
                  <pre className="text-sm text-slate-300 whitespace-pre-wrap font-sans leading-relaxed">
                    {activeTab === 'cover' ? analysis.cover_letter : analysis.hr_email}
                  </pre>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
