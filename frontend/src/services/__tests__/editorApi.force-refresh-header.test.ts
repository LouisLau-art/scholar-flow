import { beforeEach, describe, expect, it, vi } from 'vitest'

import { EditorApi } from '@/services/editorApi'

vi.mock('@/services/auth', () => ({
  authService: {
    getAccessToken: vi.fn().mockResolvedValue('mock-token'),
  },
}))

describe('EditorApi force refresh header', () => {
  beforeEach(() => {
    EditorApi.invalidateManuscriptsProcessCache()
    EditorApi.invalidateAEWorkspaceCache()
    EditorApi.invalidateManagingWorkspaceCache()
    globalThis.fetch = vi.fn()
  })

  it('adds x-sf-force-refresh when forcing process fetch', async () => {
    ;(globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, data: [] }),
    })

    await EditorApi.getManuscriptsProcess({}, { force: true })

    const call = (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0]
    const init = call[1] || {}
    const headers = (init.headers || {}) as Record<string, string>
    expect(headers['x-sf-force-refresh']).toBe('1')
  })

  it('adds x-sf-force-refresh when forcing AE workspace fetch', async () => {
    ;(globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: async () => [],
    })

    await EditorApi.getAEWorkspace(1, 20, { force: true })

    const call = (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0]
    const init = call[1] || {}
    const headers = (init.headers || {}) as Record<string, string>
    expect(headers['x-sf-force-refresh']).toBe('1')
  })

  it('adds x-sf-force-refresh when forcing managing workspace fetch', async () => {
    ;(globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: async () => [],
    })

    await EditorApi.getManagingWorkspace(1, 20, 'abc', { force: true })

    const call = (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0]
    const init = call[1] || {}
    const headers = (init.headers || {}) as Record<string, string>
    expect(headers['x-sf-force-refresh']).toBe('1')
  })
})

