// === ScholarFlow 核心业务接口定义 ===

export type ManuscriptStatus = 
  | 'draft' 
  | 'submitted' 
  | 'returned_for_revision' 
  | 'under_review' 
  | 'approved' 
  | 'pending_payment' 
  | 'published' 
  | 'rejected'
  | 'high_similarity';

export interface Manuscript {
  id: string;
  title: string;
  abstract: string;
  file_path?: string;
  author_id: string;
  editor_id?: string;
  status: ManuscriptStatus;
  owner_id?: string;
  // backward-compatible
  kpi_owner_id?: string;
  created_at: string;
  updated_at: string;
}

export interface ReviewReport {
  id: string;
  manuscript_id: string;
  reviewer_id: string;
  token: string;
  expiry_date: string;
  status: 'invited' | 'accepted' | 'completed' | 'expired' | 'revoked';
  content?: string;
  score?: number;
}

export interface Invoice {
  id: string;
  manuscript_id: string;
  amount: number;
  pdf_url?: string;
  status: 'unpaid' | 'paid';
  confirmed_at?: string;
}

export type NotificationType = 'submission' | 'review_invite' | 'decision' | 'chase' | 'system'

export interface Notification {
  id: string
  user_id: string
  manuscript_id?: string | null
  action_url?: string | null
  type: NotificationType
  title: string
  content: string
  is_read: boolean
  created_at: string
}

// === Analytics Dashboard Types ===

export interface KPISummary {
  new_submissions_month: number
  total_pending: number
  avg_first_decision_days: number
  yearly_acceptance_rate: number
  apc_revenue_month: number
  apc_revenue_year: number
}

export interface TrendData {
  month: string
  submission_count: number
  acceptance_count: number
}

export interface GeoData {
  country: string
  submission_count: number
}

export interface PipelineData {
  stage: string
  count: number
}

export interface DecisionData {
  decision: string
  count: number
}

export interface AnalyticsSummaryResponse {
  kpi: KPISummary
}

export interface TrendsResponse {
  trends: TrendData[]
  pipeline: PipelineData[]
  decisions: DecisionData[]
}

export interface GeoResponse {
  countries: GeoData[]
}

export interface EditorEfficiencyItem {
  editor_id: string
  editor_name: string
  editor_email?: string | null
  handled_count: number
  avg_first_decision_days: number
}

export interface StageDurationItem {
  stage: 'pre_check' | 'under_review' | 'decision' | 'production'
  avg_days: number
  sample_size: number
}

export interface SLAAlertItem {
  manuscript_id: string
  title: string
  status: string
  journal_id?: string | null
  journal_title?: string | null
  editor_id?: string | null
  editor_name?: string | null
  owner_id?: string | null
  owner_name?: string | null
  overdue_tasks_count: number
  max_overdue_days: number
  earliest_due_at?: string | null
  severity: 'low' | 'medium' | 'high'
}

export interface AnalyticsManagementResponse {
  editor_ranking: EditorEfficiencyItem[]
  stage_durations: StageDurationItem[]
  sla_alerts: SLAAlertItem[]
}
