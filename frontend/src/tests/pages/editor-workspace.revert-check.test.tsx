import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AEWorkspacePanel } from '@/components/editor/AEWorkspacePanel'
import { editorService } from '@/services/editorService'

vi.mock('@/services/editorService', () => ({
  editorService: {
    getAEWorkspace: vi.fn(),
    submitTechnicalCheck: vi.fn(),
    revertTechnicalCheck: vi.fn(),
  },
}))

describe('AEWorkspacePanel revert technical check', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('opens and closes revert dialog without empty manuscript placeholder', async () => {
    ;(editorService.getAEWorkspace as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([
      {
        id: 'ms-under-review-1',
        title: 'Social Media Influence on Consumer Behavior',
        status: 'under_review',
        updated_at: '2026-03-05T00:00:00Z',
      },
    ])

    render(<AEWorkspacePanel />)

    fireEvent.click(await screen.findByRole('button', { name: 'Undo Submit Check' }))
    expect(await screen.findByText('Undo Submit Technical Check')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    await waitFor(() => {
      expect(screen.queryByText('Undo Submit Technical Check')).not.toBeInTheDocument()
      expect(screen.queryByText(/稿件：—/)).not.toBeInTheDocument()
      expect(screen.queryByText(/Untitled Manuscript/)).not.toBeInTheDocument()
    })
  })

  it('validates reason length and submits revert request', async () => {
    ;(editorService.getAEWorkspace as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([
      {
        id: 'ms-under-review-2',
        title: 'Artificial Intelligence in Financial Markets',
        status: 'under_review',
        updated_at: '2026-03-05T00:00:00Z',
      },
    ])
    ;(editorService.revertTechnicalCheck as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      message: 'Technical check reverted',
      data: {
        id: 'ms-under-review-2',
        status: 'pre_check',
        pre_check_status: 'technical',
      },
    })

    render(<AEWorkspacePanel />)

    fireEvent.click(await screen.findByRole('button', { name: 'Undo Submit Check' }))
    expect(await screen.findByText('Undo Submit Technical Check')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Confirm' }))
    expect(await screen.findByText('请填写至少 10 个字的回退原因。')).toBeInTheDocument()

    fireEvent.change(screen.getByPlaceholderText('请说明回退原因（至少 10 个字）'), {
      target: { value: '误触提交外审，撤回到技术检查阶段' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Confirm' }))

    await waitFor(() => {
      expect(editorService.revertTechnicalCheck).toHaveBeenCalledWith('ms-under-review-2', {
        reason: '误触提交外审，撤回到技术检查阶段',
        source: 'ae_workspace',
      })
    })

    await waitFor(() => {
      expect(screen.queryByText('Undo Submit Technical Check')).not.toBeInTheDocument()
    })
  })
})
