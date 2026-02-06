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

      if (p === `/api/v1/auth/magic-link/verify`) {
        return fulfillJson(route, 200, {
          success: true,
          data: {
            assignment_id: a1,
          },
        })
      }
      if (p === `/api/v1/reviewer/assignments/${a1}/workspace`) {
        return fulfillJson(route, 200, {
          success: true,
          data: {
            manuscript: { id: 'm1', title: 'Magic Link Manuscript A', pdf_url: 'https://example.com/a.pdf' },
            review_report: {
              id: null,
              status: 'pending',
              comments_for_author: '',
              confidential_comments_to_editor: '',
              recommendation: 'minor_revision',
              attachments: [],
            },
            permissions: { can_submit: true, is_read_only: false },
          },
        })
      }
      if (p === `/api/v1/reviewer/assignments/${a2}/workspace`) {
        return fulfillJson(route, 200, {
          success: true,
          data: {
            manuscript: { id: 'm2', title: 'Magic Link Manuscript B', pdf_url: 'https://example.com/b.pdf' },
            review_report: {
              id: null,
              status: 'pending',
              comments_for_author: '',
              confidential_comments_to_editor: '',
              recommendation: 'minor_revision',
              attachments: [],
            },
            permissions: { can_submit: true, is_read_only: false },
          },
        })
      }

      if (p.endsWith('/submit') && req.method() === 'POST') {
        return fulfillJson(route, 200, { success: true, data: { ok: true } })
      }

      return route.fulfill({ status: 404, body: 'not mocked' })
    })

    await page.goto(`/review/invite?token=fake&assignment_id=${a1}`)
    await expect(page).toHaveURL(new RegExp(`/reviewer/workspace/${a1}$`))
    await expect(page.getByText('Action Panel')).toBeVisible()
    await expect(page.getByText('Magic Link Manuscript A')).toBeVisible()

    await page.getByLabel('Comments for the Authors').fill('Looks good.')
    await expect(page.getByLabel('Comments for the Authors')).toHaveValue('Looks good.')

    // Switch to another assignment — form state should reset (key remount)
    await page.goto(`/review/invite?token=fake&assignment_id=${a2}`)
    await expect(page.getByText('Magic Link Manuscript B')).toBeVisible()
    await expect(page.getByLabel('Comments for the Authors')).toHaveValue('')
  })
})
