// === ScholarFlow 核心业务接口定义 ===

export type ManuscriptStatus = 
  | 'draft' 
  | 'submitted' 
  | 'returned_for_revision' 
  | 'under_review' 
  | 'approved' 
  | 'pending_payment' 
  | 'published' 
  | 'rejected';

export interface Manuscript {
  id: string;
  title: string;
  abstract: string;
  file_path?: string;
  author_id: string;
  editor_id?: string;
  status: ManuscriptStatus;
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
