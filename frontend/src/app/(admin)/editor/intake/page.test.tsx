import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import MEIntakePage from './page'
import { editorService } from '@/services/editorService'

vi.mock('@/components/layout/SiteHeader', () => ({
  default: () => <div data-testid="site-header" />,
}))

vi.mock('@/components/providers/QueryProvider', () => ({
  default: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

vi.mock('@/components/editor/ManagingWorkspacePanel', () => ({
  ManagingWorkspacePanel: ({ initialBucket }: { initialBucket?: string }) => (
    <div data-testid="managing-workspace-panel" data-initial-bucket={initialBucket}>
      Managing Workspace Panel Mock
    </div>
  ),
}))

vi.mock('@/services/editorService', () => ({
  editorService: {
    getIntakeQueue: vi.fn(),
  },
}))

describe('MEIntakePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders transition message and uses ManagingWorkspacePanel with intake bucket', async () => {
    render(<MEIntakePage />)

    // Should render the mock panel
    const panel = screen.getByTestId('managing-workspace-panel')
    expect(panel).toBeInTheDocument()
    expect(panel).toHaveAttribute('data-initial-bucket', 'intake')

    // Should NOT call getIntakeQueue
    expect(editorService.getIntakeQueue).not.toHaveBeenCalled()
  })
})
