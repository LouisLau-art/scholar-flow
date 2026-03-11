import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import DashboardPageClient from '@/components/dashboard/DashboardPageClient'

vi.mock('next/navigation', () => ({
  useSearchParams: () => new URLSearchParams(''),
}))

vi.mock('@/components/layout/SiteHeader', () => ({
  default: () => <div data-testid="site-header" />,
}))

vi.mock('@/components/ReviewerDashboard', () => ({
  default: () => <div>Reviewer Dashboard</div>,
}))

vi.mock('@/components/AdminDashboard', () => ({
  default: () => <div>Admin Dashboard</div>,
}))

vi.mock('@/services/auth', () => ({
  authService: {
    getAccessToken: vi.fn().mockResolvedValue('token'),
  },
}))

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

describe('DashboardPageClient role normalization', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('accepts comma-separated role string from SSR profile payload and still shows allowed tabs', async () => {
    render(
      <DashboardPageClient
        initialStats={{ total_submissions: 0 }}
        initialSubmissions={[]}
        initialRoles={'author,reviewer'}
        initialStatsLoaded={true}
        initialSubmissionsLoaded={true}
        initialRolesLoaded={true}
      />
    )

    await waitFor(() => {
      expect(
        screen.queryByText('当前账号未分配可访问的 Dashboard 角色，请联系管理员在 User Management 中补齐角色。')
      ).not.toBeInTheDocument()
    })

    expect(await screen.findByRole('tab', { name: /Author/i })).toBeInTheDocument()
    expect(await screen.findByRole('tab', { name: /Reviewer/i })).toBeInTheDocument()
  })

  it('accepts comma-separated role string from profile API and still shows allowed tabs', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ success: true, data: { total_submissions: 0 } }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ success: true, data: [] }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ success: true, data: { roles: 'author,reviewer' } }) })

    vi.stubGlobal('fetch', fetchMock as typeof fetch)

    render(
      <DashboardPageClient
        initialStats={null}
        initialSubmissions={[]}
        initialRoles={null}
        initialStatsLoaded={false}
        initialSubmissionsLoaded={false}
        initialRolesLoaded={false}
      />
    )

    await waitFor(() => {
      expect(
        screen.queryByText('当前账号未分配可访问的 Dashboard 角色，请联系管理员在 User Management 中补齐角色。')
      ).not.toBeInTheDocument()
    })

    expect(screen.getByRole('tab', { name: /Author/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /Reviewer/i })).toBeInTheDocument()
  })

  it('shows backend-unavailable guidance instead of role-missing copy when profile API is unavailable', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ success: true, data: { total_submissions: 0 } }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ success: true, data: [] }) })
      .mockResolvedValueOnce({ ok: false, status: 503, json: async () => ({}) })

    vi.stubGlobal('fetch', fetchMock as typeof fetch)

    render(
      <DashboardPageClient
        initialStats={null}
        initialSubmissions={[]}
        initialRoles={null}
        initialStatsLoaded={false}
        initialSubmissionsLoaded={false}
        initialRolesLoaded={false}
      />
    )

    expect(
      await screen.findByText('当前无法加载 Dashboard 权限信息，后端服务可能暂时不可用。')
    ).toBeInTheDocument()
    expect(
      screen.queryByText('当前账号未分配可访问的 Dashboard 角色，请联系管理员在 User Management 中补齐角色。')
    ).not.toBeInTheDocument()
  })

  it('shows author tab when the user already has submissions even if author role is missing', async () => {
    render(
      <DashboardPageClient
        initialStats={{ total_submissions: 1 }}
        initialSubmissions={[
          {
            id: 'm-1',
            title: 'Reviewer Submitted Paper',
            status: 'pre_check',
            created_at: '2026-03-11T00:00:00.000000+00:00',
          },
        ]}
        initialRoles={['reviewer']}
        initialStatsLoaded={true}
        initialSubmissionsLoaded={true}
        initialRolesLoaded={true}
      />
    )

    expect(await screen.findByRole('tab', { name: /Author/i })).toBeInTheDocument()
    expect(await screen.findByRole('tab', { name: /Reviewer/i })).toBeInTheDocument()
    expect(screen.getByText('Reviewer Submitted Paper')).toBeInTheDocument()
  })
})
