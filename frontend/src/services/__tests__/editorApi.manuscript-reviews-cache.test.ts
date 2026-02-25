import { beforeEach, describe, expect, it, vi } from 'vitest'

import { EditorApi } from '@/services/editorApi'

vi.mock('@/services/auth', () => ({
  authService: {
    getAccessToken: vi.fn().mockResolvedValue('mock-token'),
  },
}))

describe('EditorApi manuscript reviews cache', () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn()
  })

  it('hits short cache for same manuscript id within ttl', async () => {
    ;(globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, data: [{ id: 'rr-1' }] }),
    })

    const first = await EditorApi.getManuscriptReviews('m-cache-hit')
    const second = await EditorApi.getManuscriptReviews('m-cache-hit')

    expect(first.success).toBe(true)
    expect(second.success).toBe(true)
    expect(globalThis.fetch).toHaveBeenCalledTimes(1)
  })

  it('bypasses cache when force=true', async () => {
    ;(globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, data: [{ id: 'rr-2' }] }),
    })

    await EditorApi.getManuscriptReviews('m-force')
    await EditorApi.getManuscriptReviews('m-force', { force: true })

    expect(globalThis.fetch).toHaveBeenCalledTimes(2)
  })

  it('does not share cache across different manuscript ids', async () => {
    ;(globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, data: [] }),
    })

    await EditorApi.getManuscriptReviews('m-a')
    await EditorApi.getManuscriptReviews('m-b')

    expect(globalThis.fetch).toHaveBeenCalledTimes(2)
  })
})

