import { test, expect } from '@playwright/test'
import { fulfillJson } from '../utils'

async function enableE2EAuthBypass(page: import('@playwright/test').Page) {
  await page.context().setExtraHTTPHeaders({ 'x-scholarflow-e2e': '1' })
}

test.describe('Reviewer magic link (mocked)', () => {
  test('invitation redirect + state reset between assignments', async ({ page }) => {
    await enableE2EAuthBypass(page)

    const a1 = '00000000-0000-0000-0000-000000000001'
    const a2 = '00000000-0000-0000-0000-000000000002'

    await page.route('**/api/v1/**', async (route) => {
      const req = route.request()
      const url = new URL(req.url())
      const p = url.pathname

      if (p === `/api/v1/reviews/magic/assignments/${a1}`) {
        return fulfillJson(route, 200, {
          success: true,
          data: {
            assignment_id: a1,
            reviewer_id: 'r1',
            manuscript: { id: 'm1', title: 'Magic Link Manuscript A' },
            review_report: null,
            latest_revision: null,
          },
        })
      }
      if (p === `/api/v1/reviews/magic/assignments/${a2}`) {
        return fulfillJson(route, 200, {
          success: true,
          data: {
            assignment_id: a2,
            reviewer_id: 'r2',
            manuscript: { id: 'm2', title: 'Magic Link Manuscript B' },
            review_report: null,
            latest_revision: null,
          },
        })
      }

      if (p.endsWith('/pdf-signed')) {
        return fulfillJson(route, 200, { success: true, data: { signed_url: 'https://example.com/x.pdf' } })
      }
      if (p.endsWith('/attachment-signed')) {
        return fulfillJson(route, 200, { success: true, data: { signed_url: null } })
      }

      if (p.endsWith('/submit') && req.method() === 'POST') {
        return fulfillJson(route, 200, { success: true, data: { ok: true } })
      }

      return route.fulfill({ status: 404, body: 'not mocked' })
    })

    await page.goto(`/review/invite?token=fake&assignment_id=${a1}`)
    await expect(page.getByRole('heading', { name: 'Review Manuscript' })).toBeVisible()
    await expect(page.getByText('Magic Link Manuscript A')).toBeVisible()

    await page.getByLabel('Comments for the Authors').fill('Looks good.')
    await expect(page.getByLabel('Comments for the Authors')).toHaveValue('Looks good.')

    // Switch to another assignment — form state should reset (key remount)
    await page.goto(`/review/invite?token=fake&assignment_id=${a2}`)
    await expect(page.getByText('Magic Link Manuscript B')).toBeVisible()
    await expect(page.getByLabel('Comments for the Authors')).toHaveValue('')
  })
})

