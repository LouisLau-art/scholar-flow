import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import EditorManuscriptDetailPage from '@/app/(admin)/editor/manuscript/[id]/page'
import { EditorApi } from '@/services/editorApi'

vi.mock('@/services/editorApi', () => ({
  EditorApi: {
    getRbacContext: vi.fn(),
    getManuscriptDetail: vi.fn(),
    getManuscriptCardsContext: vi.fn(),
    getManuscriptReviews: vi.fn(),
    patchManuscriptStatus: vi.fn(),
    updateInvoiceInfo: vi.fn(),
  },
}))

vi.mock('@/services/auth', () => ({
  authService: {
    getSession: vi.fn().mockResolvedValue({ user: { email: 'ae@test.com' } }),
  },
}))

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

vi.mock('@/components/layout/SiteHeader', () => ({
  default: () => <div data-testid="site-header" />,
}))

vi.mock('@/components/editor/FileHubCard', () => ({
  FileHubCard: () => <div data-testid="file-hub-card" />,
}))

vi.mock('@/components/editor/InternalNotebook', () => ({
  InternalNotebook: () => <div data-testid="internal-notebook" />,
}))

vi.mock('@/components/editor/InternalTasksPanel', () => ({
  InternalTasksPanel: () => <div data-testid="internal-tasks" />,
}))

vi.mock('@/components/editor/AuditLogTimeline', () => ({
  AuditLogTimeline: () => <div data-testid="audit-log-timeline" />,
}))

vi.mock('@/components/editor/BindingOwnerDropdown', () => ({
  BindingOwnerDropdown: () => <div data-testid="binding-owner" />,
}))

vi.mock('@/components/editor/BindingAssistantEditorDropdown', () => ({
  BindingAssistantEditorDropdown: () => <div data-testid="binding-ae" />,
}))

vi.mock('@/components/editor/ProductionStatusCard', () => ({
  ProductionStatusCard: () => <div data-testid="production-status" />,
}))

vi.mock('@/components/editor/ReviewerAssignmentSearch', () => ({
  ReviewerAssignmentSearch: () => <div data-testid="reviewer-assignment-search" />,
}))

vi.mock('@/components/editor/InvoiceInfoModal', () => ({
  InvoiceInfoModal: () => null,
}))

function detailPayload() {
  return {
    success: true,
    data: {
      id: 'test-id',
      title: 'Performance Manuscript',
      status: 'under_review',
      created_at: '2026-02-24T01:00:00Z',
      updated_at: '2026-02-24T02:00:00Z',
      journals: { title: 'J-Test' },
      invoice_metadata: {},
      invoice: { status: 'unpaid', amount: 0 },
      files: [],
      reviewer_invites: [],
      role_queue: {
        current_role: 'assistant_editor',
        current_assignee: null,
        current_assignee_label: 'AE Queue',
      },
      task_summary: {
        open_tasks_count: 0,
        overdue_tasks_count: 0,
        is_overdue: false,
        nearest_due_at: null,
      },
    },
  }
}

describe('Editor detail performance flow', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  beforeEach(() => {
    vi.clearAllMocks()
    ;(EditorApi.getRbacContext as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      success: true,
      data: {
        user_id: 'u-1',
        roles: ['assistant_editor'],
        normalized_roles: ['assistant_editor'],
        allowed_actions: ['manuscript:view_detail'],
        journal_scope: null,
      },
    })
    ;(EditorApi.getManuscriptDetail as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(detailPayload())
    ;(EditorApi.getManuscriptCardsContext as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      success: true,
      data: {
        task_summary: {
          open_tasks_count: 1,
          overdue_tasks_count: 0,
          is_overdue: false,
          nearest_due_at: null,
        },
        role_queue: {
          current_role: 'assistant_editor',
          current_assignee: null,
          current_assignee_label: 'AE Queue',
        },
      },
    })
    ;(EditorApi.getManuscriptReviews as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      success: true,
      data: [],
    })
  })

  it('loads detail in core-first mode with skip_cards=true', async () => {
    render(<EditorManuscriptDetailPage />)

    await screen.findByText('Performance Manuscript')

    expect(EditorApi.getManuscriptDetail).toHaveBeenCalledWith('test-id', { skipCards: true })
    await waitFor(() => {
      expect(EditorApi.getManuscriptCardsContext).toHaveBeenCalledWith('test-id', { force: false })
    })
  })

  it('shows retry entry when deferred cards loading times out', async () => {
    ;(EditorApi.getManuscriptCardsContext as unknown as ReturnType<typeof vi.fn>)
      .mockRejectedValueOnce(new Error('Task/queue cards loading timed out.'))
      .mockResolvedValueOnce({
        success: true,
        data: {
          task_summary: {
            open_tasks_count: 2,
            overdue_tasks_count: 1,
            is_overdue: true,
            nearest_due_at: '2026-02-25T08:00:00Z',
          },
          role_queue: {
            current_role: 'assistant_editor',
            current_assignee: null,
            current_assignee_label: 'AE Queue',
          },
        },
      })

    render(<EditorManuscriptDetailPage />)
    await screen.findByText('Performance Manuscript')

    const retryBtn = await screen.findByTestId('cards-context-retry')
    fireEvent.click(retryBtn)

    await waitFor(() => {
      expect(EditorApi.getManuscriptCardsContext).toHaveBeenCalledTimes(2)
    })
  })
})
