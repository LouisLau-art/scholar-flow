import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import LoginPage from '@/app/login/page'
import SignupPage from '@/app/signup/page'

vi.mock('next/link', () => ({
  default: ({ href, children, ...props }: any) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}))

describe('Auth pages accessibility baseline', () => {
  it('login page exposes explicit labels and autocomplete', () => {
    render(<LoginPage />)

    const email = screen.getByLabelText(/email address/i)
    const password = screen.getByLabelText(/^password$/i)
    const submit = screen.getByRole('button', { name: /sign in/i })

    expect(email).toHaveAttribute('id', 'login-email')
    expect(email).toHaveAttribute('autocomplete', 'email')
    expect(password).toHaveAttribute('id', 'login-password')
    expect(password).toHaveAttribute('autocomplete', 'current-password')
    expect(submit).toBeInTheDocument()
  })

  it('signup page exposes explicit labels and autocomplete', () => {
    render(<SignupPage />)

    const email = screen.getByLabelText(/university email/i)
    const password = screen.getByLabelText(/create password/i)
    const submit = screen.getByRole('button', { name: /create account/i })

    expect(email).toHaveAttribute('id', 'signup-email')
    expect(email).toHaveAttribute('autocomplete', 'email')
    expect(password).toHaveAttribute('id', 'signup-password')
    expect(password).toHaveAttribute('autocomplete', 'new-password')
    expect(submit).toBeInTheDocument()
  })
})
