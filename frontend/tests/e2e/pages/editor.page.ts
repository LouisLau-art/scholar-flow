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
    const reviewer = this.page.getByTestId(`reviewer-item-${reviewerId}`)
    await reviewer.scrollIntoViewIfNeeded()
    await reviewer.click({ force: true })
    await this.page.getByTestId('reviewer-assign').click()
  }

  // Feature 044: Pre-check workflow helpers
  async openIntakeQueue() {
    await this.page.goto('/editor/intake')
  }

  async assignAssistantEditor(aeId: string) {
    await this.page.getByRole('button', { name: 'Assign AE' }).first().click()
    await this.page.locator('select').first().selectOption(aeId)
    await this.page.getByRole('button', { name: 'Assign', exact: true }).click()
  }

  async openAEWorkspace() {
    await this.page.goto('/editor/workspace')
  }

  async submitTechnicalCheck(opts?: { decision?: 'pass' | 'revision'; comment?: string }) {
    const decision = opts?.decision ?? 'pass'
    await this.page.getByRole('button', { name: 'Submit Check' }).first().click()
    await this.page.locator('select').first().selectOption(decision)
    if (opts?.comment) {
      await this.page.locator('textarea').first().fill(opts.comment)
    }
    await this.page.getByRole('button', { name: 'Confirm' }).click()
  }

  async openAcademicQueue() {
    await this.page.goto('/editor/academic')
  }

  async submitAcademicCheck(decision: 'review' | 'decision_phase' = 'review') {
    await this.page.getByRole('button', { name: 'Make Decision' }).first().click()
    if (decision === 'review') {
      await this.page.getByLabel('Send to External Review').check()
    } else {
      await this.page.getByLabel('Proceed to Decision Phase (Reject/Revision)').check()
    }
    await this.page.getByRole('button', { name: 'Submit' }).click()
  }
}
