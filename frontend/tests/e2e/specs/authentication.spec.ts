import { test, expect } from '@playwright/test'
import { SubmissionPage } from '../pages/submission.page'
import { buildSession, seedSession } from '../utils'

test.describe('Authentication', () => {
  test('unauthenticated users see login prompt on submission', async ({ page }) => {
    const submission = new SubmissionPage(page)
    await submission.goto()
    await expect(page.getByTestId('submission-login-prompt')).toBeVisible()
  })

  test('session persists across reload', async ({ page }) => {
    await seedSession(page, buildSession())
    const submission = new SubmissionPage(page)
    await submission.goto()
    await expect(page.getByTestId('submission-user')).toContainText('test@example.com')

    await page.reload()
    await expect(page.getByTestId('submission-user')).toContainText('test@example.com')
  })
})
