import { expect, test } from '@playwright/test'
import { fulfillJson } from '../utils'

test.describe('Reviewer invite accept flow (mocked)', () => {
  test('accepts invitation and enters workspace', async ({ page }) => {
    const assignmentId = '00000000-0000-0000-0000-000000000201'
    await page.context().setExtraHTTPHeaders({ 'x-scholarflow-e2e': '1' })

    await page.route('**/api/v1/**', async (route) => {
      const req = route.request()
      const pathname = new URL(req.url()).pathname

      if (pathname === '/api/v1/auth/magic-link/verify') {
        return fulfillJson(route, 200, { success: true, data: { assignment_id: assignmentId } })
      }
      if (pathname === `/api/v1/reviewer/assignments/${assignmentId}/invite`) {
        return fulfillJson(route, 200, {
          success: true,
          data: {
            assignment: {
              assignment_id: assignmentId,
              status: 'invited',
              due_at: null,
              decline_reason: null,
              decline_note: null,
              timeline: { invited_at: '2026-02-01T00:00:00Z', opened_at: null, accepted_at: null, declined_at: null, submitted_at: null },
            },
            manuscript: { id: 'm1', title: 'Accept Flow Manuscript', abstract: 'A test abstract.' },
            window: { min_due_date: '2026-02-06', max_due_date: '2026-02-09', default_due_date: '2026-02-07' },
            can_open_workspace: false,
          },
        })
      }
      if (pathname === `/api/v1/reviewer/assignments/${assignmentId}/accept` && req.method() === 'POST') {
        return fulfillJson(route, 200, { success: true, data: { status: 'accepted', idempotent: false, due_at: '2026-02-07T00:00:00Z' } })
      }
      if (pathname === `/api/v1/reviewer/assignments/${assignmentId}/workspace`) {
        return fulfillJson(route, 200, {
          success: true,
          data: {
            manuscript: { id: 'm1', title: 'Accept Flow Manuscript', abstract: 'A test abstract.', pdf_url: 'https://example.com/a.pdf' },
            review_report: { id: null, status: 'pending', comments_for_author: '', confidential_comments_to_editor: '', recommendation: 'minor_revision', attachments: [] },
            permissions: { can_submit: true, is_read_only: false },
          },
        })
      }

      return route.fulfill({ status: 404, body: 'not mocked' })
    })

    await page.goto(`/review/invite?token=fake-token&assignment_id=${assignmentId}`)
    await expect(page.getByText('Accept Flow Manuscript')).toBeVisible()
    await expect(page.getByText('Due date', { exact: true })).toBeVisible()
    await expect(page.getByRole('button', { name: '2026-02-07' })).toBeVisible()
    await Promise.all([
      page.waitForURL(new RegExp(`/reviewer/workspace/${assignmentId}$`)),
      page.getByRole('button', { name: 'Accept & Continue' }).click(),
    ])
    await expect(page).toHaveURL(new RegExp(`/reviewer/workspace/${assignmentId}$`))
    await expect(page.getByRole('heading', { name: 'Review Comment' })).toBeVisible()
  })
})
