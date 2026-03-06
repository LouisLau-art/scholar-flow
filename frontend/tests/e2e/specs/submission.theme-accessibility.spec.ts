import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

import { buildSession, fulfillJson, seedSession } from '../utils'

async function enableE2EAuthBypass(page: import('@playwright/test').Page) {
  await page.context().setExtraHTTPHeaders({ 'x-scholarflow-e2e': '1' })
}

async function mockSubmitPageApis(page: import('@playwright/test').Page) {
  await page.route('**/api/_sf_events**', async (route) => {
    await route.fulfill({ status: 204, body: '' })
  })
  await page.route('**/api/v1/public/journals', async (route) => {
    await fulfillJson(route, 200, {
      success: true,
      data: [
        {
          id: 'journal-e2e',
          title: 'E2E Journal',
          slug: 'e2e-journal',
        },
      ],
    })
  })
}

test.describe('Submit Page Theme + Accessibility Guard', () => {
  test.beforeEach(async ({ page }) => {
    await enableE2EAuthBypass(page)
    await seedSession(page, buildSession('00000000-0000-0000-0000-000000000123', 'author-e2e@example.com'))
    await mockSubmitPageApis(page)
    await page.emulateMedia({ reducedMotion: 'reduce' })
  })

  test('dark theme uses high-contrast semantic button tokens', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'dark', reducedMotion: 'reduce' })
    await page.goto('/submit')

    const shell = page.getByTestId('submission-page-shell')
    await expect(shell).toBeVisible()

    const finalize = page.getByTestId('submission-finalize')
    await expect(finalize).toBeVisible()
    await expect(finalize).toHaveClass(/bg-primary/)
    await expect(finalize).toHaveClass(/text-primary-foreground/)

    const wordUpload = page.getByTestId('submission-word-file')
    const coverUpload = page.getByTestId('submission-cover-letter-file')
    const pdfUpload = page.getByTestId('submission-file')

    await expect(wordUpload).toHaveClass(/file:bg-primary/)
    await expect(wordUpload).toHaveClass(/file:text-primary-foreground/)

    await expect(coverUpload).toHaveClass(/file:bg-primary/)
    await expect(coverUpload).toHaveClass(/file:text-primary-foreground/)

    await expect(pdfUpload).toHaveClass(/file:bg-primary/)
    await expect(pdfUpload).toHaveClass(/file:text-primary-foreground/)
  })

  test('submission form has no serious WCAG A/AA violations', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'dark', reducedMotion: 'reduce' })
    await page.goto('/submit')

    const shell = page.getByTestId('submission-page-shell')
    await expect(shell).toBeVisible()

    const accessibilityScanResults = await new AxeBuilder({ page })
      .include('[data-testid="submission-page-shell"]')
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze()

    expect(accessibilityScanResults.violations).toEqual([])
  })
})

