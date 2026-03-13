import type { Page } from '@playwright/test'

export class LoginPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/login')
    await this.page.waitForLoadState('networkidle')
  }

  async login(email: string, password: string) {
    await this.page.getByTestId('login-email').fill(email)
    await this.page.getByTestId('login-password').fill(password)
    await Promise.all([
      this.page.waitForResponse(
        (response) =>
          response.url().includes('/auth/v1/token?grant_type=password') &&
          response.request().method() === 'POST' &&
          response.ok(),
        { timeout: 20000 }
      ),
      this.page.getByTestId('login-submit').click(),
    ])

    await this.page.waitForURL((url) => !url.pathname.startsWith('/login'), {
      timeout: 20000,
    })
  }
}
