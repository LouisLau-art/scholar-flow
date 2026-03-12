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
    EditorApi.invalidateManagingWorkspaceCache()
    EditorApi.invalidateIntakeQueueCache()
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

  it('assignAE posts request body and invalidates managing workspace cache', async () => {
    ;(globalThis.fetch as any).mockImplementation((url: string) => {
      if (url.includes('managing-workspace')) {
        return Promise.resolve({
          ok: true,
          json: async () => ([]),
        })
      }
      return Promise.resolve({
        ok: true,
        json: async () => ({ message: 'ok' }),
      })
    })

    // Pre-populate cache
    await EditorApi.getManagingWorkspace(1, 20)
    expect(globalThis.fetch).toHaveBeenCalledTimes(1)

    await EditorApi.assignAE('manuscript-1', { ae_id: 'ae-1', idempotency_key: 'idem-1' })

    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/v1/editor/manuscripts/manuscript-1/assign-ae',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ ae_id: 'ae-1', idempotency_key: 'idem-1' }),
      })
    )

    // Should fetch again because cache was invalidated
    await EditorApi.getManagingWorkspace(1, 20)
    expect(globalThis.fetch).toHaveBeenCalledTimes(3)
  })

  it('submitIntakeRevision invalidates managing workspace cache', async () => {
    ;(globalThis.fetch as any).mockImplementation((url: string) => {
      if (url.includes('managing-workspace')) {
        return Promise.resolve({
          ok: true,
          json: async () => ([]),
        })
      }
      return Promise.resolve({
        ok: true,
        json: async () => ({ message: 'ok' }),
      })
    })

    await EditorApi.getManagingWorkspace(1, 20)
    expect(globalThis.fetch).toHaveBeenCalledTimes(1)

    await EditorApi.submitIntakeRevision('manuscript-1', 'reason')

    await EditorApi.getManagingWorkspace(1, 20)
    expect(globalThis.fetch).toHaveBeenCalledTimes(3)
  })

  it('submitTechnicalCheck posts decision and comment and invalidates managing workspace cache', async () => {
    ;(globalThis.fetch as any).mockImplementation((url: string) => {
      if (url.includes('managing-workspace')) {
        return Promise.resolve({
          ok: true,
          json: async () => ([]),
        })
      }
      return Promise.resolve({
        ok: true,
        json: async () => ({ message: 'ok' }),
      })
    })

    await EditorApi.getManagingWorkspace(1, 20)
    expect(globalThis.fetch).toHaveBeenCalledTimes(1)

    await EditorApi.submitTechnicalCheck('manuscript-2', { decision: 'revision', comment: 'need fixes' })

    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/v1/editor/manuscripts/manuscript-2/submit-check',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ decision: 'revision', comment: 'need fixes' }),
      })
    )

    await EditorApi.getManagingWorkspace(1, 20)
    expect(globalThis.fetch).toHaveBeenCalledTimes(3)
  })

  it('revertTechnicalCheck invalidates managing workspace cache', async () => {
    ;(globalThis.fetch as any).mockImplementation((url: string) => {
      if (url.includes('managing-workspace')) {
        return Promise.resolve({
          ok: true,
          json: async () => ([]),
        })
      }
      return Promise.resolve({
        ok: true,
        json: async () => ({ message: 'ok' }),
      })
    })

    await EditorApi.getManagingWorkspace(1, 20)
    expect(globalThis.fetch).toHaveBeenCalledTimes(1)

    await EditorApi.revertTechnicalCheck('manuscript-1', { reason: 'revert' })

    await EditorApi.getManagingWorkspace(1, 20)
    expect(globalThis.fetch).toHaveBeenCalledTimes(3)
  })

  it('submitAcademicCheck invalidates managing workspace cache', async () => {
    ;(globalThis.fetch as any).mockImplementation((url: string) => {
      if (url.includes('managing-workspace')) {
        return Promise.resolve({
          ok: true,
          json: async () => ([]),
        })
      }
      return Promise.resolve({
        ok: true,
        json: async () => ({ message: 'ok' }),
      })
    })

    await EditorApi.getManagingWorkspace(1, 20)
    expect(globalThis.fetch).toHaveBeenCalledTimes(1)

    await EditorApi.submitAcademicCheck('manuscript-1', { decision: 'pass' })

    await EditorApi.getManagingWorkspace(1, 20)
    expect(globalThis.fetch).toHaveBeenCalledTimes(3)
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

  it('listAcademicEditors passes manuscript id and search query', async () => {
    ;(globalThis.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, data: [] }),
    })

    await EditorApi.listAcademicEditors('manuscript-7', 'zhang')

    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/v1/editor/academic-editors?manuscript_id=manuscript-7&search=zhang',
      expect.anything()
    )
  })
})
