import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ProductionQueuePage from './page'
import { EditorApi } from '@/services/editorApi'

vi.mock('@/components/layout/SiteHeader', () => ({
  default: () => <div data-testid="site-header" />,
}))

vi.mock('@/components/providers/QueryProvider', () => ({
  default: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

vi.mock('@/services/editorApi', () => ({
  EditorApi: {
    listMyProductionQueue: vi.fn(),
  },
}))

describe('ProductionQueuePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(EditorApi.listMyProductionQueue).mockResolvedValue({
      success: true,
      data: [],
    } as any)
  })

  it('uses SOP wording in the queue description', async () => {
    render(<ProductionQueuePage />)

    await waitFor(() => {
      expect(EditorApi.listMyProductionQueue).toHaveBeenCalledWith(80)
    })

    expect(screen.getByText('Production Queue')).toBeInTheDocument()
    expect(screen.getByText('仅展示当前分配给你的活跃生产轮次：SOP 阶段处理、作者校对与发布前核准。')).toBeInTheDocument()
    expect(screen.queryByText(/layout_editor_id/i)).not.toBeInTheDocument()
  })
})
