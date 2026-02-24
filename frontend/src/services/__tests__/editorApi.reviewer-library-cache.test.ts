import { beforeEach, describe, expect, it, vi } from 'vitest'

import { EditorApi } from '@/services/editorApi'

vi.mock('@/services/auth', () => ({
  authService: {
    getAccessToken: vi.fn().mockResolvedValue('mock-token'),
  },
}))

describe('EditorApi reviewer library cache', () => {
  beforeEach(() => {
    EditorApi.invalidateReviewerSearchCache()
    globalThis.fetch = vi.fn()
  })

  it('hits short cache for same manuscript/query/role-scope within ttl', async () => {
    ;(globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, data: [{ id: 'r-1' }], policy: { cooldown_days: 30 } }),
    })

    const first = await EditorApi.searchReviewerLibrary('  AI  ', 120, 'ms-1', { roleScopeKey: 'admin,managing_editor' })
    const second = await EditorApi.searchReviewerLibrary('ai', 120, 'ms-1', { roleScopeKey: 'managing_editor,admin' })

    expect(first.success).toBe(true)
    expect(second.success).toBe(true)
    expect(globalThis.fetch).toHaveBeenCalledTimes(1)
  })

  it('misses cache when manuscript or role scope changes', async () => {
    ;(globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, data: [{ id: 'r-1' }] }),
    })

    await EditorApi.searchReviewerLibrary('nlp', 80, 'ms-1', { roleScopeKey: 'admin' })
    await EditorApi.searchReviewerLibrary('nlp', 80, 'ms-2', { roleScopeKey: 'admin' })
    await EditorApi.searchReviewerLibrary('nlp', 80, 'ms-2', { roleScopeKey: 'assistant_editor' })

    expect(globalThis.fetch).toHaveBeenCalledTimes(3)
  })

  it('deduplicates inflight request and allows explicit invalidation', async () => {
    let resolveFetch: ((value: unknown) => void) | null = null
    const deferred = new Promise((resolve) => {
      resolveFetch = resolve
    })
    ;(globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockReturnValue(deferred)

    const pendingA = EditorApi.searchReviewerLibrary('physics', 60, 'ms-3', { roleScopeKey: 'admin' })
    const pendingB = EditorApi.searchReviewerLibrary('physics', 60, 'ms-3', { roleScopeKey: 'admin' })

    await vi.waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledTimes(1)
    })

    resolveFetch?.({
      ok: true,
      json: async () => ({ success: true, data: [{ id: 'r-9' }] }),
    })

    await Promise.all([pendingA, pendingB])

    EditorApi.invalidateReviewerSearchCache({ manuscriptId: 'ms-3', roleScopeKey: 'admin' })

    ;(globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, data: [{ id: 'r-9' }] }),
    })

    await EditorApi.searchReviewerLibrary('physics', 60, 'ms-3', { roleScopeKey: 'admin' })
    expect(globalThis.fetch).toHaveBeenCalledTimes(2)
  })
})
