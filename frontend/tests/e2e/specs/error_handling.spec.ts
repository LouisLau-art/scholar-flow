import { test, expect } from '@playwright/test'
import { SubmissionPage } from '../pages/submission.page'
import { buildSession, fulfillJson, seedSession } from '../utils'

test('upload failure shows error message', async ({ page }) => {
  await seedSession(page, buildSession())
  const submission = new SubmissionPage(page)

  await page.route('**/storage/v1/object/manuscripts/**', async (route) => {
    await route.fulfill({ status: 200, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) })
  })

  await page.route('**/api/v1/manuscripts/upload', async (route) => {
    await fulfillJson(route, 500, { success: false, message: 'Upload failed' })
  })

  await submission.goto()
  const pdfBuffer = Buffer.from('%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF')
  await submission.uploadPdf(pdfBuffer)

  await expect(page.getByText('AI parsing failed. Please fill manually.')).toBeVisible()
})
