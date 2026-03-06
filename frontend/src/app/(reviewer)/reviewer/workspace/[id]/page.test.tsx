import { render, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ReviewerWorkspacePage from './page'

const { replaceMock, toastErrorMock } = vi.hoisted(() => ({
  replaceMock: vi.fn(),
  toastErrorMock: vi.fn(),
}))

vi.mock('next/navigation', () => ({
  useParams: () => ({ id: 'assign-redirect' }),
  useRouter: () => ({
    replace: replaceMock,
  }),
}))

vi.mock('sonner', () => ({
  toast: {
    error: toastErrorMock,
  },
}))

describe('ReviewerWorkspacePage', () => {
  beforeEach(() => {
    replaceMock.mockReset()
    toastErrorMock.mockReset()
    globalThis.fetch = vi.fn(async () => ({
      ok: false,
      json: async () => ({
        detail: {
          code: 'INVITE_ACCEPT_REQUIRED',
          message: 'Please accept invitation first',
        },
      }),
    })) as unknown as typeof fetch
  })

  it('redirects back to invite surface when workspace access requires acceptance', async () => {
    render(<ReviewerWorkspacePage />)

    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith('/review/invite?assignment_id=assign-redirect')
    })
  })
})
