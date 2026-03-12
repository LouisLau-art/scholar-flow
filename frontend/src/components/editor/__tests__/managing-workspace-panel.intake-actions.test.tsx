import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ManagingWorkspacePanel } from '@/components/editor/ManagingWorkspacePanel'
import { editorService } from '@/services/editorService'

vi.mock('@/services/editorService', () => ({
  editorService: {
    getManagingWorkspace: vi.fn(),
  },
}))

describe('ManagingWorkspacePanel intake actions', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders quick actions for intake bucket', async () => {
    ;(editorService.getManagingWorkspace as any).mockResolvedValue([
      {
        id: 'intake-1',
        title: 'Intake Manuscript',
        status: 'pre_check',
        pre_check_status: 'intake',
        workspace_bucket: 'intake',
        updated_at: '2026-03-12T10:00:00Z',
      },
    ])

    render(<ManagingWorkspacePanel />)

    await waitFor(() => {
      expect(editorService.getManagingWorkspace).toHaveBeenCalled()
    })

    expect(await screen.findByText('Intake 待分派')).toBeInTheDocument()
    expect(screen.getByText('Intake Manuscript')).toBeInTheDocument()
    
    expect(screen.getByText('通过并分配 AE')).toBeInTheDocument()
    expect(screen.getByText('技术退回')).toBeInTheDocument()
  })

  it('does not render quick actions for other buckets like under_review', async () => {
    ;(editorService.getManagingWorkspace as any).mockResolvedValue([
      {
        id: 'review-1',
        title: 'Review Manuscript',
        status: 'under_review',
        workspace_bucket: 'under_review',
        updated_at: '2026-03-12T10:00:00Z',
      },
    ])

    render(<ManagingWorkspacePanel />)

    await waitFor(() => {
      expect(editorService.getManagingWorkspace).toHaveBeenCalled()
    })

    expect(await screen.findByText('外审进行中')).toBeInTheDocument()
    expect(screen.getByText('Review Manuscript')).toBeInTheDocument()
    
    expect(screen.queryByText('通过并分配 AE')).not.toBeInTheDocument()
    expect(screen.queryByText('技术退回')).not.toBeInTheDocument()
    expect(screen.getByText('Open Detail')).toBeInTheDocument()
  })
})
