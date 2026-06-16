export interface SourceChunk {
  chunk_id: string
  content: string
  source_file: string
  page_number: number | null
  similarity_score: number
  chunk_index: number
}

export interface ConfidenceInfo {
  level: 'high' | 'medium' | 'low'
  score: number
  label: string
}

export interface FaithfulnessInfo {
  verdict: 'FAITHFUL' | 'PARTIALLY_FAITHFUL' | 'NOT_FAITHFUL' | 'UNKNOWN'
  explanation: string
  checked: boolean
}

export interface QueryResponse {
  answer: string
  sources: SourceChunk[]
  question: string
  preprocessed_question: string
  total_sources_found: number
  processing_time_ms: number
  collection_searched: string
  search_mode: string
  reranking_applied: boolean
  confidence: ConfidenceInfo | null
  faithfulness: FaithfulnessInfo | null
}

export interface DocumentInfo {
  document_id: string
  filename: string
  total_chunks: number
  collection_name: string
  uploaded_at: string
}

export interface UploadResponse {
  document_id: string
  filename: string
  total_chunks: number
  collection_name: string
  message: string
}

export interface SourceIngestionResponse {
  document_id: string
  source_label: string
  source_type: string
  total_chunks: number
  collection_name: string
  message: string
}

export interface AnalyticsStats {
  total_queries: number
  avg_processing_time_ms: number
  avg_sources_found: number
  confidence_distribution: { high: number; medium: number; low: number }
  faithfulness_distribution: {
    FAITHFUL: number
    PARTIALLY_FAITHFUL: number
    NOT_FAITHFUL: number
    UNKNOWN: number
  }
  search_mode_distribution: { hybrid: number; semantic: number; keyword: number }
  slowest_queries: Array<{ query: string; time_ms: number }>
  recent_queries: Array<{
    ts: string
    query: string
    confidence: string
    faithfulness: string
    mode: string
    time_ms: number
  }>
}

export interface ResumeAnalysis {
  match_score: number
  summary: string
  matched_keywords: string[]
  missing_keywords: string[]
  strengths: string[]
  gaps: string[]
  recommendations: string[]
  cover_letter: string
  hr_email: string
}

export type SearchMode = 'hybrid' | 'semantic' | 'keyword'
export type SourceType = 'pdf' | 'web' | 'github' | 'youtube'

export interface IndexedSource {
  id: string
  name: string
  type: SourceType
  chunks: number
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  data?: QueryResponse
}
