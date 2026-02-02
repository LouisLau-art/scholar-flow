import type { Page } from '@playwright/test'

export class SubmissionPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/submit')
  }

  async uploadPdf(buffer: Buffer) {
    await this.page.waitForSelector('[data-testid="submission-file"]', { state: 'attached' })
    await this.page.setInputFiles('[data-testid="submission-file"]', {
      name: 'manuscript.pdf',
      mimeType: 'application/pdf',
      buffer,
    })
  }

  async fillMetadata(title: string, abstract: string) {
    await this.page.getByTestId('submission-title').fill(title)
    await this.page.getByTestId('submission-abstract').fill(abstract)
  }

  async finalize() {
    await this.page.getByTestId('submission-finalize').click()
  }
}
