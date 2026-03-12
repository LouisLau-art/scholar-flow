import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import MEIntakePage from './page'
import { editorService } from '@/services/editorService'

const assignModalMock = vi.fn()

vi.mock('@/components/layout/SiteHeader', () => ({
  default: () => <div data-testid="site-header" />,
}))

vi.mock('@/components/providers/QueryProvider', () => ({
  default: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

vi.mock('@/components/AssignAEModal', () => ({
  AssignAEModal: (props: {
    isOpen: boolean
    mode?: 'pass_and_assign' | 'bind_only'
    manuscriptId: string
  }) => {
    assignModalMock(props)
    return props.isOpen ? <div data-testid="assign-ae-modal">{props.mode}</div> : null
  },
}))

vi.mock('@/services/assistantEditorsCache', () => ({
  getAssistantEditors: vi.fn().mockResolvedValue([]),
}))

vi.mock('@/services/editorService', () => ({
  editorService: {
    getIntakeQueue: vi.fn(),
    submitIntakeRevision: vi.fn(),
  },
}))

describe('MEIntakePage waiting author actions', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('keeps waiting-author manuscripts assignable and opens bind-only mode', async () => {
    ;(editorService.getIntakeQueue as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([
      {
        id: 'wait-1',
        title: 'Waiting Author No AE',
        pre_check_status: 'awaiting_resubmit',
        waiting_resubmit: true,
        waiting_resubmit_reason: 'Please update the formatting.',
        author: { full_name: 'Author One' },
        journal: { title: 'Computer Science' },
      },
      {
        id: 'wait-2',
        title: 'Waiting Author With AE',
        pre_check_status: 'awaiting_resubmit',
        waiting_resubmit: true,
        waiting_resubmit_reason: 'Please revise the figures.',
        assistant_editor_id: 'ae-2',
        author: { full_name: 'Author Two' },
        journal: { title: 'Computer Science' },
      },
    ])

    render(<MEIntakePage />)

    await waitFor(() => {
      expect(editorService.getIntakeQueue).toHaveBeenCalled()
    })

    expect(await screen.findByText('Waiting Author No AE')).toBeInTheDocument()
    expect(screen.queryByText('等待作者修回（不可操作）')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: '分配 AE' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '改派 AE' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '分配 AE' }))

    expect(await screen.findByTestId('assign-ae-modal')).toHaveTextContent('bind_only')
    expect(assignModalMock).toHaveBeenLastCalledWith(
      expect.objectContaining({
        isOpen: true,
        manuscriptId: 'wait-1',
        mode: 'bind_only',
      }),
    )
  })
})
