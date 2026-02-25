import { beforeEach, describe, expect, it, vi } from 'vitest'

import { EditorApi } from '@/services/editorApi'

vi.mock('@/services/auth', () => ({
  authService: {
    getAccessToken: vi.fn().mockResolvedValue('mock-token'),
  },
}))

describe('EditorApi manuscripts process cache', () => {
  beforeEach(() => {
    EditorApi.invalidateManuscriptsProcessCache()
    globalThis.fetch = vi.fn()
  })

  it('hits short cache for same filter set regardless of statuses order', async () => {
    ;(globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, data: [{ id: 'ms-1' }] }),
    })

    const first = await EditorApi.getManuscriptsProcess({
      q: '  quantum  ',
      statuses: ['under_review', 'decision'],
      overdueOnly: false,
    })
    const second = await EditorApi.getManuscriptsProcess({
      q: 'quantum',
      statuses: ['decision', 'under_review'],
      overdueOnly: false,
    })

    expect(first.success).toBe(true)
    expect(second.success).toBe(true)
    expect(globalThis.fetch).toHaveBeenCalledTimes(1)
  })

  it('bypasses cache when force=true', async () => {
    ;(globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, data: [{ id: 'ms-2' }] }),
    })

    const filters = { statuses: ['pre_check'] }
    await EditorApi.getManuscriptsProcess(filters)
    await EditorApi.getManuscriptsProcess(filters, { force: true })

    expect(globalThis.fetch).toHaveBeenCalledTimes(2)
  })

  it('deduplicates inflight requests for same filter key', async () => {
    let resolveFetch: (value: unknown) => void = () => {}
    const deferred = new Promise((resolve) => {
      resolveFetch = resolve as (value: unknown) => void
    })
    ;(globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockReturnValue(deferred)

    const filters = { statuses: ['under_review'], overdueOnly: true }
    const pendingA = EditorApi.getManuscriptsProcess(filters)
    const pendingB = EditorApi.getManuscriptsProcess(filters)

    await vi.waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledTimes(1)
    })

    resolveFetch({
      ok: true,
      json: async () => ({ success: true, data: [{ id: 'ms-3' }] }),
    })

    await Promise.all([pendingA, pendingB])
    expect(globalThis.fetch).toHaveBeenCalledTimes(1)
  })
})
