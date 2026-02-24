import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ManuscriptsProcessPanel } from '@/components/editor/ManuscriptsProcessPanel'
import { EditorApi } from '@/services/editorApi'

vi.mock('next/navigation', () => ({
  useSearchParams: () => new URLSearchParams(''),
}))

vi.mock('@/services/editorApi', () => ({
  EditorApi: {
    getManuscriptsProcess: vi.fn(),
    getRbacContext: vi.fn(),
  },
}))

vi.mock('@/components/editor/ProcessFilterBar', () => ({
  ProcessFilterBar: () => <div data-testid="process-filter-bar" />,
}))

vi.mock('@/components/editor/ManuscriptTable', () => ({
  ManuscriptTable: ({ rows, emptyText }: { rows: Array<{ id: string; title: string }>; emptyText: string }) => (
    <div data-testid="manuscript-table-mock">
      {rows.length === 0 ? <div>{emptyText}</div> : null}
      {rows.map((row) => (
        <div key={row.id}>{row.title}</div>
      ))}
    </div>
  ),
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

describe('ManuscriptsProcessPanel staged loading', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(EditorApi.getRbacContext as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ success: false })
  })

  it('uses cached rows for instant paint and refreshes in background', async () => {
    ;(EditorApi.getManuscriptsProcess as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      success: true,
      data: [{ id: 'ms-1', title: 'Cached Manuscript' }],
    })

    const firstRender = render(<ManuscriptsProcessPanel />)
    await screen.findByText('Cached Manuscript')
    firstRender.unmount()

    const deferred = createDeferred<any>()
    ;(EditorApi.getManuscriptsProcess as unknown as ReturnType<typeof vi.fn>).mockImplementationOnce(() => deferred.promise)

    render(<ManuscriptsProcessPanel />)

    expect(screen.getByText('Cached Manuscript')).toBeInTheDocument()
    expect(screen.getByText('Syncing latest data...')).toBeInTheDocument()

    deferred.resolve({ success: true, data: [{ id: 'ms-1', title: 'Cached Manuscript' }] })

    await waitFor(() => {
      expect(EditorApi.getManuscriptsProcess).toHaveBeenCalledTimes(2)
    })
  })
})
