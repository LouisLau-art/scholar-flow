import { expect, test } from '@playwright/test'

import { buildSession, fulfillJson, seedSession } from '../utils'

async function enableE2EAuthBypass(page: import('@playwright/test').Page) {
  await page.context().setExtraHTTPHeaders({ 'x-scholarflow-e2e': '1' })
}

test.describe('Reviewer management delivery evidence (mocked backend)', () => {
  test('shows delivery status in reviewer management and history modal', async ({ page }) => {
    await enableE2EAuthBypass(page)
    await seedSession(page, buildSession('00000000-0000-0000-0000-000000000001', 'editor@example.com'))

    const manuscriptId = '00000000-0000-0000-0000-000000000301'
    const reviewerId = 'reviewer-1'
    const assignmentId = 'ra-1'

    await page.route('**/api/v1/**', async (route) => {
      const req = route.request()
      const pathname = new URL(req.url()).pathname

      if (pathname === '/api/v1/cms/menu') {
        return fulfillJson(route, 200, { success: true, data: [] })
      }
      if (pathname === '/api/v1/user/profile') {
        return fulfillJson(route, 200, {
          success: true,
          data: { roles: ['admin', 'managing_editor', 'assistant_editor'] },
        })
      }
      if (pathname === '/api/v1/notifications') {
        return fulfillJson(route, 200, { success: true, data: [] })
      }
      if (pathname === '/api/v1/editor/rbac/context') {
        return fulfillJson(route, 200, {
          success: true,
          data: {
            user_id: '00000000-0000-0000-0000-000000000001',
            roles: ['admin', 'managing_editor', 'assistant_editor'],
            normalized_roles: ['admin', 'managing_editor', 'assistant_editor'],
            allowed_actions: [
              'process:view',
              'manuscript:view_detail',
              'review:assign',
              'review:view_assignments',
              'review:unassign',
            ],
            journal_scope: {
              enforcement_enabled: false,
              allowed_journal_ids: [],
              is_admin: true,
            },
          },
        })
      }
      if (pathname === `/api/v1/editor/manuscripts/${manuscriptId}` && req.method() === 'GET') {
        return fulfillJson(route, 200, {
          success: true,
          data: {
            id: manuscriptId,
            title: 'Reviewer Delivery Manuscript',
            status: 'under_review',
            updated_at: '2026-03-09T12:00:00Z',
            created_at: '2026-03-09T10:00:00Z',
            is_deferred_context_loaded: true,
            journals: { title: 'Journal C' },
            owner: { full_name: 'Owner User', email: 'owner@example.com' },
            editor: { full_name: 'Editor User', email: 'editor@example.com' },
            assistant_editor: { id: 'ae-1', full_name: 'AE User', email: 'ae@example.com' },
            assistant_editor_id: 'ae-1',
            role_queue: {
              current_role: 'assistant_editor',
              current_assignee: { id: 'ae-1', full_name: 'AE User', email: 'ae@example.com' },
            },
            files: [],
            signed_files: {},
            task_summary: {
              open_tasks_count: 0,
              overdue_tasks_count: 0,
              is_overdue: false,
              nearest_due_at: null,
            },
            reviewer_invites: [
              {
                id: assignmentId,
                reviewer_id: reviewerId,
                reviewer_name: 'Reviewer User',
                reviewer_email: 'reviewer@example.com',
                status: 'invited',
                round_number: 1,
                due_at: '2026-03-16T00:00:00Z',
                invited_at: '2026-03-09T10:05:00Z',
                opened_at: '2026-03-09T10:15:00Z',
                accepted_at: null,
                declined_at: null,
                last_reminded_at: null,
                submitted_at: null,
                latest_email_status: 'sent',
                latest_email_at: '2026-03-09T10:05:03Z',
                latest_email_error: null,
                email_events: [
                  {
                    assignment_id: assignmentId,
                    manuscript_id: manuscriptId,
                    status: 'sent',
                    event_type: 'invitation',
                    created_at: '2026-03-09T10:05:03Z',
                    error_message: null,
                  },
                  {
                    assignment_id: assignmentId,
                    manuscript_id: manuscriptId,
                    status: 'queued',
                    event_type: 'invitation',
                    created_at: '2026-03-09T10:05:00Z',
                    error_message: null,
                  },
                ],
              },
            ],
            author_response_history: [],
          },
        })
      }
      if (pathname === `/api/v1/editor/manuscripts/${manuscriptId}/cards-context`) {
        return fulfillJson(route, 200, {
          success: true,
          data: {
            task_summary: {
              open_tasks_count: 0,
              overdue_tasks_count: 0,
              is_overdue: false,
              nearest_due_at: null,
            },
            role_queue: {
              current_role: 'assistant_editor',
              current_assignee: { id: 'ae-1', full_name: 'AE User', email: 'ae@example.com' },
              current_assignee_label: null,
              assigned_at: '2026-03-09T10:00:00Z',
              technical_completed_at: null,
              academic_completed_at: null,
            },
          },
        })
      }
      if (pathname === `/api/v1/manuscripts/${manuscriptId}/reviews`) {
        return fulfillJson(route, 200, { success: true, data: [] })
      }
      if (pathname === '/api/v1/reviews/email-templates') {
        return fulfillJson(route, 200, {
          success: true,
          data: [
            {
              template_key: 'reviewer_invitation_standard',
              display_name: '审稿邀请信（标准）',
              scene: 'reviewer_assignment',
              event_type: 'invitation',
            },
          ],
        })
      }
      if (pathname === `/api/v1/reviews/reviewer-history/${reviewerId}`) {
        return fulfillJson(route, 200, {
          success: true,
          data: [
            {
              assignment_id: assignmentId,
              reviewer_id: reviewerId,
              manuscript_id: manuscriptId,
              manuscript_title: 'Reviewer Delivery Manuscript',
              manuscript_status: 'under_review',
              assignment_status: 'invited',
              round_number: 1,
              added_on: '2026-03-09T10:00:00Z',
              invited_at: '2026-03-09T10:05:00Z',
              opened_at: '2026-03-09T10:15:00Z',
              accepted_at: null,
              declined_at: null,
              decline_reason: null,
              decline_note: null,
              last_reminded_at: null,
              due_at: '2026-03-16T00:00:00Z',
              report_status: null,
              report_score: null,
              report_submitted_at: null,
              latest_email_status: 'sent',
              latest_email_at: '2026-03-09T10:05:03Z',
              latest_email_error: null,
              email_events: [
                {
                  assignment_id: assignmentId,
                  manuscript_id: manuscriptId,
                  status: 'sent',
                  event_type: 'invitation',
                  created_at: '2026-03-09T10:05:03Z',
                  error_message: null,
                },
                {
                  assignment_id: assignmentId,
                  manuscript_id: manuscriptId,
                  status: 'queued',
                  event_type: 'invitation',
                  created_at: '2026-03-09T10:05:00Z',
                  error_message: null,
                },
              ],
            },
          ],
        })
      }

      return fulfillJson(route, 200, { success: true, data: [] })
    })

    await page.goto(`/editor/manuscript/${manuscriptId}`, { waitUntil: 'domcontentloaded' })

    await expect(page.getByRole('heading', { name: 'Reviewer Delivery Manuscript' })).toBeVisible({ timeout: 15000 })
    await expect(page.getByText('Reviewer Management')).toBeVisible()
    await expect(page.getByText(/Delivery: sent/i)).toBeVisible()
    await expect(page.getByText('Reviewer User', { exact: true })).toBeVisible()

    await page.getByTestId(`reviewer-history-${assignmentId}`).click()

    await expect(page.getByRole('dialog')).toBeVisible()
    await expect(page.getByText(/Invitations History \(Reviewer User\)/i)).toBeVisible()
    await expect(page.getByText(/sent invitation/i)).toBeVisible()
    await expect(page.getByText(/queued invitation/i)).toBeVisible()
  })
})
