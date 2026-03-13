import type { Locator, Page } from '@playwright/test'

export class AuthorManuscriptPage {
  constructor(private page: Page) {}

  async goto(manuscriptId: string) {
    await this.page.goto(`/dashboard/author/manuscripts/${manuscriptId}`, { waitUntil: 'domcontentloaded' })
  }

  title(name: string): Locator {
    return this.page.getByRole('heading', { name, exact: true })
  }

  statusHeading(): Locator {
    return this.page.getByRole('heading', { name: 'Current Status', exact: true })
  }

  fieldLabel(label: string): Locator {
    return this.page.getByText(label, { exact: true })
  }

  fieldValue(value: string): Locator {
    return this.page.getByText(value, { exact: true })
  }
}
