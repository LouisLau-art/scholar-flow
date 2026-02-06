import { expect, test } from '@playwright/test'
import { fulfillJson } from '../utils'

test.describe('Reviewer invite decline flow (mocked)', () => {
  test('declines invitation and shows final state', async ({ page }) => {
    const assignmentId = '00000000-0000-0000-0000-000000000202'
    await page.context().setExtraHTTPHeaders({ 'x-scholarflow-e2e': '1' })

    let declined = false

    await page.route('**/api/v1/**', async (route) => {
      const req = route.request()
      const pathname = new URL(req.url()).pathname

      if (pathname === '/api/v1/auth/magic-link/verify') {
        return fulfillJson(route, 200, { success: true, data: { assignment_id: assignmentId } })
      }
      if (pathname === `/api/v1/reviewer/assignments/${assignmentId}/decline` && req.method() === 'POST') {
        declined = true
        return fulfillJson(route, 200, { success: true, data: { status: 'declined', idempotent: false } })
      }
      if (pathname === `/api/v1/reviewer/assignments/${assignmentId}/invite`) {
        return fulfillJson(route, 200, {
          success: true,
          data: {
            assignment: {
              assignment_id: assignmentId,
              status: declined ? 'declined' : 'invited',
              due_at: null,
              decline_reason: declined ? 'too_busy' : null,
              decline_note: declined ? 'No bandwidth this week' : null,
              timeline: {
                invited_at: '2026-02-01T00:00:00Z',
                opened_at: '2026-02-01T00:01:00Z',
                accepted_at: null,
                declined_at: declined ? '2026-02-02T00:00:00Z' : null,
                submitted_at: null,
              },
            },
            manuscript: { id: 'm2', title: 'Decline Flow Manuscript', abstract: null },
            window: { min_due_date: '2026-02-06', max_due_date: '2026-02-09', default_due_date: '2026-02-07' },
            can_open_workspace: false,
          },
        })
      }

      return route.fulfill({ status: 404, body: 'not mocked' })
    })

    await page.goto(`/review/invite?token=fake-token&assignment_id=${assignmentId}`)
    await expect(page.getByText('Decline Flow Manuscript')).toBeVisible()
    await page.getByLabel('Reason').selectOption('too_busy')
    await page.getByLabel('Note (optional)').fill('No bandwidth this week')
    await page.getByRole('button', { name: 'Decline Invitation' }).click()
    await expect(page.getByText(/You declined this invitation/i)).toBeVisible()
    await expect(page.getByText(/No further action available/i)).toBeVisible()
  })
})

