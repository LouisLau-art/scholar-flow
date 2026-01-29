import { test, expect } from '@playwright/test'
import { SubmissionPage } from '../pages/submission.page'
import { fulfillJson, seedSession } from '../utils'

test('frontend uses consistent /api/v1 paths', async ({ page }) => {
  const requested = new Set<string>()

  await page.route('**/api/v1/**', async (route) => {
    const url = new URL(route.request().url())
    requested.add(url.pathname)

    if (url.pathname === '/api/v1/stats/author') {
      await fulfillJson(route, 200, { success: true, data: { total_submissions: 0 } })
      return
    }
    if (url.pathname === '/api/v1/editor/pipeline') {
      await fulfillJson(route, 200, { success: true, data: { pending_quality: [], under_review: [], pending_decision: [], published: [] } })
      return
    }
    if (url.pathname === '/api/v1/manuscripts/upload') {
      await fulfillJson(route, 200, { success: true, data: { title: 'Parsed', abstract: 'Parsed', authors: [] } })
      return
    }

    await fulfillJson(route, 200, { success: true, data: {} })
  })

  await page.goto('/dashboard')
  await page.getByRole('tab', { name: /Editor/i }).click()

  await seedSession(page)
  const submission = new SubmissionPage(page)
  await submission.goto()
  const pdfBuffer = Buffer.from('%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF')
  await submission.uploadPdf(pdfBuffer)

  expect(requested).toContain('/api/v1/stats/author')
  expect(requested).toContain('/api/v1/editor/pipeline')
  expect(requested).toContain('/api/v1/manuscripts/upload')
})
