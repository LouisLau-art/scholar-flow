import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { InternalTasksPanel } from '@/components/editor/InternalTasksPanel'
import { EditorApi } from '@/services/editorApi'

vi.mock('@/services/editorApi', () => ({
  EditorApi: {
    listInternalTasks: vi.fn(),
    listInternalStaff: vi.fn(),
    createInternalTask: vi.fn(),
    patchInternalTask: vi.fn(),
    getInternalTaskActivity: vi.fn(),
  },
}))

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

describe('InternalTasksPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(EditorApi.listInternalStaff as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      success: true,
      data: [{ id: 'u1', full_name: 'Alice Editor', email: 'alice@example.com' }],
    })
    ;(EditorApi.getInternalTaskActivity as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ success: true, data: [] })
  })

  it('shows disabled hint for task that cannot be edited', async () => {
    ;(EditorApi.listInternalTasks as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      success: true,
      data: [
        {
          id: 't1',
          manuscript_id: 'm1',
          title: 'Locked Task',
          assignee_user_id: 'u1',
          status: 'todo',
          priority: 'medium',
          due_at: '2026-02-10T08:00:00Z',
          created_by: 'u1',
          can_edit: false,
          is_overdue: false,
          assignee: { id: 'u1', full_name: 'Alice Editor', email: 'alice@example.com' },
        },
      ],
    })

    render(<InternalTasksPanel manuscriptId="m1" />)

    await waitFor(() => {
      expect(EditorApi.listInternalTasks).toHaveBeenCalledWith('m1')
    })

    expect(await screen.findByText('Only the assignee or internal editor can update this task.')).toBeInTheDocument()
    const selectTrigger = await screen.findByRole('combobox', { name: 'Task Locked Task status' })
    expect(selectTrigger).toBeDisabled()
  })

  it('updates task status when editor changes status', async () => {
    ;(EditorApi.listInternalTasks as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      success: true,
      data: [
        {
          id: 't2',
          manuscript_id: 'm1',
          title: 'Follow up',
          assignee_user_id: 'u1',
          status: 'todo',
          priority: 'medium',
          due_at: '2026-02-10T08:00:00Z',
          created_by: 'u1',
          can_edit: true,
          is_overdue: false,
          assignee: { id: 'u1', full_name: 'Alice Editor', email: 'alice@example.com' },
        },
      ],
    })
    ;(EditorApi.patchInternalTask as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      success: true,
      data: {
        id: 't2',
        manuscript_id: 'm1',
        title: 'Follow up',
        assignee_user_id: 'u1',
        status: 'done',
        priority: 'medium',
        due_at: '2026-02-10T08:00:00Z',
        created_by: 'u1',
        can_edit: true,
        is_overdue: false,
      },
    })

    render(<InternalTasksPanel manuscriptId="m1" />)

    const selectTrigger = await screen.findByRole('combobox', { name: 'Task Follow up status' })
    fireEvent.click(selectTrigger)
    fireEvent.click(await screen.findByRole('option', { name: 'Done' }))

    await waitFor(() => {
      expect(EditorApi.patchInternalTask).toHaveBeenCalledWith('m1', 't2', { status: 'done' })
    })

    await waitFor(() => {
      expect(screen.getByRole('combobox', { name: 'Task Follow up status' })).toHaveTextContent('Done')
    })
  })
})
