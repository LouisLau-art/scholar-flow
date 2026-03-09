import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import SettingsPage from '@/app/settings/page'

vi.mock('@/components/layout/SiteHeader', () => ({
  default: () => <div data-testid="site-header" />,
}))

vi.mock('@/hooks/useProfile', () => ({
  useProfile: vi.fn(() => ({
    profile: null,
    isLoading: false,
    error: new Error('Failed to fetch profile'),
    saveProfile: vi.fn(),
    isSaving: false,
    changePassword: vi.fn(),
  })),
}))

vi.mock('@/components/settings/ProfileForm', () => ({
  ProfileForm: () => <div>ProfileForm</div>,
}))

vi.mock('@/components/settings/AcademicForm', () => ({
  AcademicForm: () => <div>AcademicForm</div>,
}))

vi.mock('@/components/settings/AvatarUpload', () => ({
  AvatarUpload: () => <div>AvatarUpload</div>,
}))

vi.mock('@/components/settings/PasswordChangeForm', () => ({
  PasswordChangeForm: () => <div>PasswordChangeForm</div>,
}))

describe('SettingsPage', () => {
  it('shows an explicit unavailable message when profile loading fails', () => {
    render(<SettingsPage />)

    expect(screen.getByTestId('site-header')).toBeInTheDocument()
    expect(screen.getByText('当前无法加载账号设置，请稍后重试。')).toBeInTheDocument()
    expect(screen.getByText('后端服务或个人资料接口当前不可用。')).toBeInTheDocument()
  })
})
