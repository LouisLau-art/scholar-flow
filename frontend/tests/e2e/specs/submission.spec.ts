import { test, expect } from '@playwright/test'
import { SubmissionPage } from '../pages/submission.page'
import { buildSession, fulfillJson, seedSession } from '../utils'

test.describe('Submission flow', () => {
  test('PDF upload and submission succeeds', async ({ page }) => {
    await seedSession(page, buildSession())
    const submission = new SubmissionPage(page)

    await page.route('**/api/v1/manuscripts/upload', async (route) => {
      await fulfillJson(route, 200, {
        success: true,
        data: { title: 'Parsed Title', abstract: 'Parsed Abstract', authors: [] },
      })
    })
    await page.route('**/api/v1/manuscripts', async (route) => {
      await fulfillJson(route, 200, {
        success: true,
        data: { id: 'mock-id', title: 'Parsed Title', abstract: 'Parsed Abstract' },
      })
    })

    await submission.goto()
    const pdfBuffer = Buffer.from('%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF')
    await submission.uploadPdf(pdfBuffer)

    await expect(page.getByTestId('submission-title')).toHaveValue('Parsed Title')
    await submission.finalize()
    await page.waitForURL('**/')
  })

  test('empty form keeps submit disabled', async ({ page }) => {
    await seedSession(page, buildSession())
    const submission = new SubmissionPage(page)
    await submission.goto()
    await expect(page.getByTestId('submission-finalize')).toBeDisabled()
  })
})
