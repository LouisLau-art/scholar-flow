// === 查重报告前端接口定义 ===

export type PlagiarismStatus = 'pending' | 'running' | 'completed' | 'failed'

export interface PlagiarismReport {
  id: string
  manuscript_id: string
  external_id?: string
  similarity_score?: number
  report_url?: string
  status: PlagiarismStatus
  retry_count: number
  error_log?: string
  created_at: string
  updated_at: string
}

export interface PlagiarismStatusResponse {
  success: boolean
  data: PlagiarismReport
}
