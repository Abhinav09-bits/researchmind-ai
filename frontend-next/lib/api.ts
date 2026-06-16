import type {
  QueryResponse, UploadResponse, SourceIngestionResponse,
  AnalyticsStats, ResumeAnalysis, SearchMode,
} from './types'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api/v1'

async function request<T>(path: string, init: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, init)
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
  return data as T
}

export async function sendQuery(
  question: string,
  searchMode: SearchMode,
  enableReranking: boolean,
): Promise<QueryResponse> {
  return request('/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, search_mode: searchMode, enable_reranking: enableReranking, preprocess_query: true }),
  })
}

export async function uploadPdf(file: File): Promise<UploadResponse> {
  const form = new FormData()
  form.append('file', file)
  return request('/documents/upload', { method: 'POST', body: form })
}

export async function ingestWeb(url: string): Promise<SourceIngestionResponse> {
  return request('/sources/web', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  })
}

export async function ingestGitHub(repo: string, branch: string, github_token?: string): Promise<SourceIngestionResponse> {
  return request('/sources/github', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ repo, branch, github_token: github_token || null }),
  })
}

export async function ingestYouTube(url: string): Promise<SourceIngestionResponse> {
  return request('/sources/youtube', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  })
}

export async function getAnalytics(): Promise<AnalyticsStats> {
  return request('/analytics/stats', { method: 'GET' })
}

export async function analyzeResume(file: File, jobDescription: string): Promise<ResumeAnalysis> {
  const form = new FormData()
  form.append('file', file)
  form.append('job_description', jobDescription)
  return request('/resume/analyze', { method: 'POST', body: form })
}
