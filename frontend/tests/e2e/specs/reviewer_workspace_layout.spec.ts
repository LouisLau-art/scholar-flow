import { expect, test } from '@playwright/test'
import { fulfillJson } from '../utils'

test.describe('Reviewer Workspace layout (mocked)', () => {
  test('loads immersive layout with PDF + action panel', async ({ page }) => {
    const assignmentId = '00000000-0000-0000-0000-000000000101'
    await page.context().setExtraHTTPHeaders({ 'x-scholarflow-e2e': '1' })

    await page.route('**/api/v1/**', async (route) => {
      const req = route.request()
      const pathname = new URL(req.url()).pathname

      if (pathname === `/api/v1/reviewer/assignments/${assignmentId}/workspace`) {
        return fulfillJson(route, 200, {
          success: true,
          data: {
            manuscript: {
              id: 'm-1',
              title: 'Reviewer Workspace Mock',
              abstract: 'Abstract',
              pdf_url: 'https://example.com/manuscript.pdf',
            },
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
      if (pathname === `/api/v1/reviewer/assignments/${assignmentId}/submit` && req.method() === 'POST') {
        return fulfillJson(route, 200, { success: true, data: { status: 'completed' } })
      }
      if (pathname === `/api/v1/reviewer/assignments/${assignmentId}/attachments` && req.method() === 'POST') {
        return fulfillJson(route, 200, {
          success: true,
          data: { path: `assignments/${assignmentId}/a.pdf`, url: 'https://example.com/a.pdf' },
        })
      }
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
              timeline: {
                invited_at: '2026-02-01T00:00:00Z',
                opened_at: '2026-02-01T00:01:00Z',
                accepted_at: null,
                declined_at: null,
                submitted_at: null,
              },
            },
            manuscript: {
              id: 'm-1',
              title: 'Reviewer Workspace Mock',
              abstract: 'Abstract',
            },
            window: {
              min_due_date: '2026-02-06',
              max_due_date: '2026-02-09',
              default_due_date: '2026-02-06',
            },
            can_open_workspace: false,
          },
        })
      }
      if (pathname === `/api/v1/reviewer/assignments/${assignmentId}/accept` && req.method() === 'POST') {
        return fulfillJson(route, 200, { success: true, data: { status: 'accepted', idempotent: false } })
      }
      return route.fulfill({ status: 404, body: 'not mocked' })
    })

    await page.goto(`/review/invite?token=fake-token&assignment_id=${assignmentId}`)
    await expect(page).toHaveURL(new RegExp(`/review/invite\\?assignment_id=${assignmentId}$`))
    await page.getByRole('button', { name: 'Accept & Continue' }).click()
    await expect(page).toHaveURL(new RegExp(`/reviewer/workspace/${assignmentId}$`))
    await expect(page.getByText('Reviewer Workspace', { exact: true })).toBeVisible()
    await expect(page.getByText('Action Panel')).toBeVisible()
    await expect(page.getByTitle('Manuscript PDF')).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Reviewer Workspace Mock' })).toBeVisible()
    await expect(page.getByText('ScholarFlow', { exact: false })).toHaveCount(0)
  })
})
