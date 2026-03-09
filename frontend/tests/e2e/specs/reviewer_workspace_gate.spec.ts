import { expect, test } from '@playwright/test'

import { fulfillJson } from '../utils'

test.describe('Reviewer workspace gate (mocked)', () => {
  test('redirects back to invite page when invitation has not been accepted', async ({ page }) => {
    const assignmentId = '00000000-0000-0000-0000-000000000203'
    await page.context().setExtraHTTPHeaders({ 'x-scholarflow-e2e': '1' })

    await page.route('**/api/v1/**', async (route) => {
      const pathname = new URL(route.request().url()).pathname

      if (pathname === `/api/v1/reviewer/assignments/${assignmentId}/workspace`) {
        return fulfillJson(route, 403, {
          success: false,
          detail: {
            code: 'INVITE_ACCEPT_REQUIRED',
            message: 'Reviewer must accept invitation before opening workspace.',
          },
        })
      }

      if (pathname === `/api/v1/reviewer/assignments/${assignmentId}/invite`) {
        return fulfillJson(route, 200, {
          success: true,
          data: {
            assignment: {
              assignment_id: assignmentId,
              status: 'invited',
              due_at: '2026-03-16T00:00:00Z',
              decline_reason: null,
              decline_note: null,
              timeline: {
                invited_at: '2026-03-09T00:00:00Z',
                opened_at: '2026-03-09T00:05:00Z',
                accepted_at: null,
                declined_at: null,
                submitted_at: null,
              },
            },
            manuscript: {
              id: 'm-gate',
              title: 'Workspace Gate Manuscript',
              abstract: 'This invite must be accepted before workspace access is allowed.',
            },
            window: {
              min_due_date: '2026-03-14',
              max_due_date: '2026-03-20',
              default_due_date: '2026-03-16',
            },
            can_open_workspace: false,
          },
        })
      }

      return route.fulfill({ status: 404, body: 'not mocked' })
    })

    await page.goto(`/reviewer/workspace/${assignmentId}`)

    await expect(page).toHaveURL(new RegExp(`/review/invite\\?assignment_id=${assignmentId}$`))
    await expect(page.getByText('Workspace Gate Manuscript')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Accept & Continue' })).toBeVisible()
  })
})
