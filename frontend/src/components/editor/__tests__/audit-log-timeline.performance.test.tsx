import { act, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AuditLogTimeline } from '@/components/editor/AuditLogTimeline'
import { EditorApi } from '@/services/editorApi'

vi.mock('@/services/editorApi', () => ({
  EditorApi: {
    getTimelineContext: vi.fn(),
  },
}))

describe('AuditLogTimeline deferred loading', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('loads timeline context only after viewport activation', async () => {
    let observerCallback: ((entries: Array<{ isIntersecting: boolean }>) => void) | null = null

    class FakeObserver {
      constructor(cb: typeof observerCallback) {
        observerCallback = cb
      }
      observe() {}
      disconnect() {}
    }

    ;(globalThis as any).IntersectionObserver = FakeObserver

    ;(EditorApi.getTimelineContext as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      success: true,
      data: {
        audit_logs: [],
        comments: [],
        tasks: [
          {
            id: 'task-1',
            title: 'Follow up reviewer',
            status: 'todo',
            created_at: '2026-02-24T08:00:00Z',
            creator: { full_name: 'AE User', email: 'ae@example.com' },
          },
        ],
        task_activities: [],
      },
    })

    render(<AuditLogTimeline manuscriptId="ms-1" />)

    expect(EditorApi.getTimelineContext).not.toHaveBeenCalled()

    await act(async () => {
      observerCallback?.([{ isIntersecting: true }])
    })

    await waitFor(() => {
      expect(EditorApi.getTimelineContext).toHaveBeenCalledWith('ms-1', { taskLimit: 50, activityLimit: 500 })
    })

    expect(await screen.findByText('内部任务创建')).toBeInTheDocument()
    expect(screen.getByText('Follow up reviewer')).toBeInTheDocument()
  })
})
