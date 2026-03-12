import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ManagingWorkspacePanel } from '@/components/editor/ManagingWorkspacePanel'
import { editorService } from '@/services/editorService'
import { authService } from '@/services/auth'

vi.mock('@/services/editorService', () => ({
  editorService: {
    getManagingWorkspace: vi.fn(),
  },
}))

vi.mock('@/services/auth', () => ({
  authService: {
    getSession: vi.fn(),
  },
}))

describe('ManagingWorkspacePanel error state', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('waits for session before fetching and shows auth gate', async () => {
    // Hang the session fetch forever
    ;(authService.getSession as any).mockImplementation(() => new Promise(() => {}))
    ;(editorService.getManagingWorkspace as any).mockResolvedValue([])

    render(<ManagingWorkspacePanel />)

    expect(screen.getByText('正在验证登录态...')).toBeInTheDocument()
    expect(editorService.getManagingWorkspace).not.toHaveBeenCalled()
  })

  it('shows error state when fetch fails without data', async () => {
    ;(authService.getSession as any).mockResolvedValue({})
    ;(editorService.getManagingWorkspace as any).mockRejectedValue(new Error('Network Error'))

    render(<ManagingWorkspacePanel />)

    await waitFor(() => {
      expect(screen.getByText(/加载失败/)).toBeInTheDocument()
    })
    
    expect(screen.getByText('重试')).toBeInTheDocument()
    expect(screen.queryByText('No manuscripts in current scope.')).not.toBeInTheDocument()
  })

  it('shows lightweight error if old data exists', async () => {
    ;(authService.getSession as any).mockResolvedValue({})
    
    // First call succeeds
    ;(editorService.getManagingWorkspace as any).mockResolvedValueOnce([
      { id: '1', title: 'Old Manuscript', workspace_bucket: 'intake', status: 'pre_check', updated_at: '2026-03-12T10:00:00Z' }
    ])
    // Second call fails
    .mockRejectedValueOnce(new Error('Network Error'))

    render(<ManagingWorkspacePanel />)

    await waitFor(() => {
      expect(screen.getByText('Old Manuscript')).toBeInTheDocument()
    })

    // Trigger a refetch which will fail
    const refreshBtn = screen.getByRole('button', { name: /刷新列表/i })
    fireEvent.click(refreshBtn)

    await waitFor(() => {
      expect(screen.getByText(/数据同步失败，请重试/)).toBeInTheDocument()
    })
    
    // Old data should still be there
    expect(screen.getByText('Old Manuscript')).toBeInTheDocument()
  })
})
