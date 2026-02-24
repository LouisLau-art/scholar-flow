export type EditorPerfScenario =
  | 'editor_detail'
  | 'editor_process'
  | 'editor_workspace'
  | 'reviewer_search_repeat'

export type PerformanceEnvironment = 'staging' | 'local-ci'

export type PerformanceBaselineRecord = {
  baseline_id?: string
  environment: PerformanceEnvironment
  scenario: EditorPerfScenario
  sample_set_id: string
  p50_interactive_ms: number
  p95_interactive_ms: number
  first_screen_request_count: number
  captured_at: string
  captured_by: string
  notes?: string
}

export type LoadStageSnapshot = {
  snapshot_id?: string
  scenario: EditorPerfScenario
  manuscript_id?: string
  core_ready_ms: number
  deferred_ready_ms?: number
  core_requests: number
  deferred_requests?: number
  error_count: number
}

export type CandidateSearchContext = {
  manuscript_id: string
  normalized_query: string
  role_scope_key: string
  limit: number
  cache_ttl_sec: number
}

export type CandidateSearchCacheEntry<TPayload = unknown> = {
  context: CandidateSearchContext
  result_count: number
  stored_at: string
  expires_at: string
  source: 'network' | 'cache'
  payload: TPayload
}

export type RegressionGateResult = {
  gate_run_id: string
  baseline_ref: string
  regression_ratio: number
  threshold_ratio: number
  functional_tests_passed: boolean
  performance_checks_passed: boolean
  status: 'passed' | 'failed'
  report_path: string
}
