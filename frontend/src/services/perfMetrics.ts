import type { EditorPerfScenario, LoadStageSnapshot } from '@/types/performance'

type RecorderOptions = {
  manuscriptId?: string
}

type RecorderResult = {
  markCoreReady: () => void
  markDeferredReady: () => void
  addCoreRequest: () => void
  addDeferredRequest: () => void
  addError: () => void
  snapshot: () => LoadStageSnapshot
}

function nowMs(): number {
  if (typeof performance !== 'undefined' && typeof performance.now === 'function') {
    return performance.now()
  }
  return Date.now()
}

export function createBrowserPerfRecorder(
  scenario: EditorPerfScenario,
  options: RecorderOptions = {}
): RecorderResult {
  const startedAt = nowMs()
  let coreReadyMs = 0
  let deferredReadyMs: number | undefined
  let coreRequests = 0
  let deferredRequests = 0
  let errorCount = 0

  const safeDelta = () => Math.max(1, Math.round(nowMs() - startedAt))

  return {
    markCoreReady: () => {
      coreReadyMs = safeDelta()
    },
    markDeferredReady: () => {
      deferredReadyMs = safeDelta()
      if (!coreReadyMs) coreReadyMs = deferredReadyMs
    },
    addCoreRequest: () => {
      coreRequests += 1
    },
    addDeferredRequest: () => {
      deferredRequests += 1
    },
    addError: () => {
      errorCount += 1
    },
    snapshot: () => ({
      scenario,
      manuscript_id: options.manuscriptId,
      core_ready_ms: coreReadyMs || safeDelta(),
      deferred_ready_ms: deferredReadyMs,
      core_requests: coreRequests,
      deferred_requests: deferredRequests || undefined,
      error_count: errorCount,
    }),
  }
}

export function percentile(values: number[], percentileValue: number): number {
  if (!Array.isArray(values) || values.length === 0) return 0
  const sorted = [...values].sort((a, b) => a - b)
  const pos = Math.ceil((percentileValue / 100) * sorted.length) - 1
  const index = Math.min(Math.max(pos, 0), sorted.length - 1)
  return sorted[index]
}
