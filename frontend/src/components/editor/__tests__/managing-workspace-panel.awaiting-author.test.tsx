import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ManagingWorkspacePanel } from '@/components/editor/ManagingWorkspacePanel'
import { editorService } from '@/services/editorService'

vi.mock('@/services/editorService', () => ({
  editorService: {
    getManagingWorkspace: vi.fn(),
  },
}))

describe('ManagingWorkspacePanel awaiting author bucket', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders revision_before_review manuscripts inside 等待作者修回 bucket with quick actions', async () => {
    ;(editorService.getManagingWorkspace as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([
      {
        id: 'wait-1',
        title: 'Waiting Author Manuscript',
        status: 'revision_before_review',
        pre_check_status: 'technical',
        workspace_bucket: 'awaiting_author' as any,
        updated_at: '2026-03-12T10:00:00Z',
        assistant_editor: {
          id: 'ae-1',
          full_name: 'AE Waiting',
          email: 'ae-waiting@example.com',
        },
        intake_return_reason: 'Missing figures',
      },
    ])

    render(<ManagingWorkspacePanel />)

    await waitFor(() => {
      expect(editorService.getManagingWorkspace).toHaveBeenCalled()
    })

    expect(await screen.findByText('等待作者修回')).toBeInTheDocument()
    expect(screen.getByText('Waiting Author Manuscript')).toBeInTheDocument()
    
    // Quick actions
    expect(screen.getByText('改派 AE')).toBeInTheDocument()
    expect(screen.getByText(/退回原因: Missing figures/)).toBeInTheDocument()
  })
})
