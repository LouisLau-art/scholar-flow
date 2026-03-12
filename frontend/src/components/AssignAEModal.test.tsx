import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AssignAEModal } from '@/components/AssignAEModal'
import { editorService } from '@/services/editorService'
import { EditorApi } from '@/services/editorApi'
import { getAssistantEditors, peekAssistantEditorsCache } from '@/services/assistantEditorsCache'

vi.mock('@/services/editorService', () => ({
  editorService: {
    assignAE: vi.fn(),
  },
}))

vi.mock('@/services/editorApi', () => ({
  EditorApi: {
    listInternalStaff: vi.fn(),
  },
}))

vi.mock('@/services/assistantEditorsCache', () => ({
  getAssistantEditors: vi.fn(),
  peekAssistantEditorsCache: vi.fn(),
}))

describe('AssignAEModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(peekAssistantEditorsCache).mockReturnValue(null)
    vi.mocked(getAssistantEditors).mockResolvedValue([
      { id: 'ae-1', full_name: 'Alice AE', email: 'alice@example.com' },
    ])
    vi.mocked(EditorApi.listInternalStaff).mockResolvedValue({ success: true, data: [] } as any)
    vi.mocked(editorService.assignAE).mockResolvedValue(undefined as never)
  })

  it('默认模式会通过并推进到 under_review', async () => {
    render(
      <AssignAEModal
        isOpen
        onClose={vi.fn()}
        manuscriptId="ms-1"
        onAssignSuccess={vi.fn()}
      />
    )

    expect(screen.getByText('通过并分配 AE')).toBeInTheDocument()

    await screen.findByText('请选择 AE')
    fireEvent.click(screen.getAllByRole('combobox')[0])
    fireEvent.click(await screen.findByRole('button', { name: /Alice AE/i }))
    fireEvent.click(screen.getByRole('button', { name: '分配并进入外审' }))

    await waitFor(() => {
      expect(editorService.assignAE).toHaveBeenCalledWith('ms-1', 'ae-1', {
        startExternalReview: true,
        bindOwnerIfEmpty: true,
        ownerId: undefined,
      })
    })
  })

  it('仅绑定模式不会推进到 under_review', async () => {
    render(
      <AssignAEModal
        isOpen
        onClose={vi.fn()}
        manuscriptId="ms-waiting"
        onAssignSuccess={vi.fn()}
        mode="bind_only"
      />
    )

    expect(screen.getByText('分配 / 改派 AE')).toBeInTheDocument()
    expect(screen.queryByText(/高级选项：Owner/)).not.toBeInTheDocument()

    await screen.findByText('请选择 AE')
    fireEvent.click(screen.getAllByRole('combobox')[0])
    fireEvent.click(await screen.findByRole('button', { name: /Alice AE/i }))
    fireEvent.click(screen.getByRole('button', { name: '保存 AE 分配' }))

    await waitFor(() => {
      expect(editorService.assignAE).toHaveBeenCalledWith('ms-waiting', 'ae-1', {
        startExternalReview: false,
        bindOwnerIfEmpty: false,
        ownerId: undefined,
      })
    })
  })
})
