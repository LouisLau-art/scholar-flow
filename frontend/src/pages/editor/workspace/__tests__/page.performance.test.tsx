import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import AEWorkspacePage from '@/pages/editor/workspace/page'
import { editorService } from '@/services/editorService'

vi.mock('@/services/editorService', () => ({
  editorService: {
    getAEWorkspace: vi.fn(),
    submitTechnicalCheck: vi.fn(),
  },
}))

vi.mock('@/components/layout/SiteHeader', () => ({
  default: () => <div data-testid="site-header" />,
}))

vi.mock('@/components/providers/QueryProvider', () => ({
  default: ({ children }: { children: any }) => <>{children}</>,
}))

type Deferred<T> = {
  promise: Promise<T>
  resolve: (value: T) => void
}

function createDeferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((res) => {
    resolve = res
  })
  return { promise, resolve }
}

describe('AEWorkspacePage performance guards', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('keeps latest workspace response when older request resolves later', async () => {
    const first = createDeferred<any[]>()
    const second = createDeferred<any[]>()

    ;(editorService.getAEWorkspace as unknown as ReturnType<typeof vi.fn>)
      .mockImplementationOnce(() => first.promise)
      .mockImplementationOnce(() => second.promise)

    render(<AEWorkspacePage />)

    const refreshBtn = await screen.findByTestId('workspace-refresh-btn')
    fireEvent.click(refreshBtn)

    second.resolve([
      {
        id: 'ms-latest',
        title: 'Latest Manuscript',
        status: 'under_review',
        updated_at: '2026-02-24T02:00:00Z',
      },
    ])

    await screen.findByText('Latest Manuscript')

    first.resolve([
      {
        id: 'ms-stale',
        title: 'Stale Manuscript',
        status: 'pre_check',
        updated_at: '2026-02-24T01:00:00Z',
      },
    ])

    await waitFor(() => {
      expect(screen.queryByText('Stale Manuscript')).not.toBeInTheDocument()
      expect(screen.getByText('Latest Manuscript')).toBeInTheDocument()
    })

    expect(editorService.getAEWorkspace).toHaveBeenCalledTimes(2)
    expect(editorService.getAEWorkspace).toHaveBeenNthCalledWith(
      2,
      1,
      20,
      expect.objectContaining({ forceRefresh: true })
    )
  })
})
