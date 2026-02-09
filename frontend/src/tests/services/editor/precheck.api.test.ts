import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { EditorApi } from '@/services/editorApi'
import { authService } from '@/services/auth'

vi.mock('@/services/auth', () => ({
  authService: {
    getAccessToken: vi.fn().mockResolvedValue('mock-token'),
  },
}))

describe('EditorApi precheck endpoints', () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('getIntakeQueue sends pagination params and bearer token', async () => {
    ;(globalThis.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => [],
    })

    await EditorApi.getIntakeQueue(2, 50)

    expect(authService.getAccessToken).toHaveBeenCalled()
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/editor/intake?page=2&page_size=50'),
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: 'Bearer mock-token' }),
      })
    )
  })

  it('assignAE posts request body', async () => {
    ;(globalThis.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => ({ message: 'ok' }),
    })

    await EditorApi.assignAE('manuscript-1', { ae_id: 'ae-1', idempotency_key: 'idem-1' })

    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/v1/editor/manuscripts/manuscript-1/assign-ae',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ ae_id: 'ae-1', idempotency_key: 'idem-1' }),
      })
    )
  })

  it('submitTechnicalCheck posts decision and comment', async () => {
    ;(globalThis.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => ({ message: 'ok' }),
    })

    await EditorApi.submitTechnicalCheck('manuscript-2', { decision: 'revision', comment: 'need fixes' })

    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/v1/editor/manuscripts/manuscript-2/submit-check',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ decision: 'revision', comment: 'need fixes' }),
      })
    )
  })

  it('listAssistantEditors passes search query', async () => {
    ;(globalThis.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, data: [] }),
    })

    await EditorApi.listAssistantEditors('alice')

    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/v1/editor/assistant-editors?search=alice',
      expect.anything()
    )
  })
})
