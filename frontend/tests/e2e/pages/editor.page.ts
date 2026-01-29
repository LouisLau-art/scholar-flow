import type { Page } from '@playwright/test'

export class EditorPage {
  constructor(private page: Page) {}

  async open() {
    await this.page.goto('/dashboard')
    await this.page.getByRole('tab', { name: /Editor/i }).click()
  }

  async openAssignModal() {
    await this.page.getByTestId('editor-tab-reviewers').click()
    await this.page.getByTestId('editor-open-assign').click()
  }

  async assignReviewer(reviewerId: string) {
    await this.page.getByTestId(`reviewer-item-${reviewerId}`).click()
    await this.page.getByTestId('reviewer-assign').click()
  }
}
