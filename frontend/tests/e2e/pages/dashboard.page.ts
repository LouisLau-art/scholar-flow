import type { Page } from '@playwright/test'

export class DashboardPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/dashboard')
  }

  async openEditorTab() {
    await this.page.getByRole('tab', { name: /Editor/i }).click()
  }

  async openReviewerTab() {
    await this.page.getByRole('tab', { name: /Reviewer/i }).click()
  }
}
