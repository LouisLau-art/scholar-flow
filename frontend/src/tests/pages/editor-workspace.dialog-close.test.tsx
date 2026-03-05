import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AEWorkspacePanel } from '@/components/editor/AEWorkspacePanel'
import { editorService } from '@/services/editorService'

vi.mock('@/services/editorService', () => ({
  editorService: {
    getAEWorkspace: vi.fn(),
    submitTechnicalCheck: vi.fn(),
  },
}))

describe('AEWorkspacePanel submit check dialog close guard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('prevents immediate reopen right after closing submit check dialog', async () => {
    ;(editorService.getAEWorkspace as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([
      {
        id: 'ms-technical-1',
        title: 'Quantum Mechanics in Modern Systems',
        status: 'pre_check',
        pre_check_status: 'technical',
        updated_at: '2026-03-05T00:00:00Z',
      },
    ])

    let now = 1_000
    const dateNowSpy = vi.spyOn(Date, 'now').mockImplementation(() => now)

    try {
      render(<AEWorkspacePanel />)

      const submitCheckBtn = await screen.findByRole('button', { name: 'Submit Check' })
      fireEvent.click(submitCheckBtn)
      expect(await screen.findByText('Submit Technical Check')).toBeInTheDocument()

      fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
      await waitFor(() => {
        expect(screen.queryByText('Submit Technical Check')).not.toBeInTheDocument()
        expect(screen.queryByText(/稿件：—/)).not.toBeInTheDocument()
        expect(screen.queryByText(/Untitled Manuscript/)).not.toBeInTheDocument()
      })

      fireEvent.click(submitCheckBtn)
      expect(screen.queryByText('Submit Technical Check')).not.toBeInTheDocument()

      now += 1201
      fireEvent.click(submitCheckBtn)
      expect(await screen.findByText('Submit Technical Check')).toBeInTheDocument()
    } finally {
      dateNowSpy.mockRestore()
    }
  })

  it('closes with top-right close button without leaving empty manuscript context visible', async () => {
    ;(editorService.getAEWorkspace as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([
      {
        id: 'ms-technical-2',
        title: 'Behavioral Economics and Digital Markets',
        status: 'pre_check',
        pre_check_status: 'technical',
        updated_at: '2026-03-05T00:00:00Z',
      },
    ])

    render(<AEWorkspacePanel />)

    const submitCheckBtn = await screen.findByRole('button', { name: 'Submit Check' })
    fireEvent.click(submitCheckBtn)
    expect(await screen.findByText('Submit Technical Check')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Close' }))

    await waitFor(() => {
      expect(screen.queryByText('Submit Technical Check')).not.toBeInTheDocument()
      expect(screen.queryByText(/稿件：—/)).not.toBeInTheDocument()
      expect(screen.queryByText(/Untitled Manuscript/)).not.toBeInTheDocument()
    })
  })
})
