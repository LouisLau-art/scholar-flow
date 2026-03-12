import { expect, test } from '@playwright/test'

import { buildSession, fulfillJson, seedSession } from '../utils'

async function enableE2EAuthBypass(page: import('@playwright/test').Page) {
  await page.context().setExtraHTTPHeaders({ 'x-scholarflow-e2e': '1' })
}

test.describe('Reviewer management delivery evidence (mocked backend)', () => {
  test('treats previous-round reviewers as explicit reuse suggestions', async ({ page }) => {
    await enableE2EAuthBypass(page)
    await seedSession(page, buildSession('00000000-0000-0000-0000-000000000001', 'editor@example.com'))

    const manuscriptId = '00000000-0000-0000-0000-000000000303'
    const assignRequests: Array<Record<string, unknown>> = []

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
            title: 'Reviewer Reselection Manuscript',
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
            reviewer_invites: [],
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
      if (pathname === `/api/v1/reviews/assignments/${manuscriptId}` && req.method() === 'GET') {
        return fulfillJson(route, 200, {
          success: true,
          meta: {
            manuscript_version: 2,
            target_round: 1,
            selection_scope: 'previous_round_reuse',
          },
          data: [
            {
              id: 'a-prev-1',
              status: 'completed',
              due_at: null,
              round_number: 1,
              reviewer_id: 'r-prev',
              reviewer_name: 'Previous Reviewer',
              reviewer_email: 'prev@example.com',
            },
          ],
        })
      }
      if (pathname === '/api/v1/editor/reviewer-library' && req.method() === 'GET') {
        return fulfillJson(route, 200, {
          success: true,
          data: [],
          pagination: { has_more: false },
          policy: { cooldown_days: 30, override_roles: ['admin', 'managing_editor'] },
        })
      }
      if (pathname === '/api/v1/reviews/assign' && req.method() === 'POST') {
        assignRequests.push(JSON.parse(req.postData() || '{}'))
        return fulfillJson(route, 200, { success: true, data: { id: 'new-assignment' } })
      }

      return fulfillJson(route, 200, { success: true, data: [] })
    })

    await page.goto(`/editor/manuscript/${manuscriptId}`, { waitUntil: 'domcontentloaded' })

    await expect(page.getByRole('heading', { name: 'Reviewer Reselection Manuscript' })).toBeVisible({ timeout: 15000 })
    await page.getByRole('button', { name: 'Manage Reviewers' }).click()

    const modal = page.getByTestId('reviewer-modal')
    await expect(modal.getByText(/Previous Round Reviewers/i)).toBeVisible()
    await expect(modal.getByText(/These reviewers are from round 1/i)).toBeVisible()
    await expect(modal.getByTestId('reviewer-assign')).toBeDisabled()

    await modal.getByTestId('reviewer-reuse-r-prev').click()
    await expect(modal.getByTestId('reviewer-assign')).toContainText('Save Selection (1)')

    await modal.getByTestId('reviewer-assign').click()

    await expect
      .poll(() => assignRequests.length, { message: 'reviewer assign request should be explicit' })
      .toBe(1)
    expect(assignRequests[0]).toMatchObject({
      manuscript_id: manuscriptId,
      reviewer_id: 'r-prev',
    })
  })

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

    const historyDialog = page.getByRole('dialog')
    await expect(historyDialog).toBeVisible()
    await expect(historyDialog.getByText(/Invitations History \(Reviewer User\)/i)).toBeVisible()
    await expect(historyDialog.getByText(/Invitation sent/i)).toBeVisible()
    await expect(historyDialog.getByText(/Invitation queued/i)).toBeVisible()
  })

  test('requires explicit handling of accepted reviewers before exiting review stage', async ({ page }) => {
    await enableE2EAuthBypass(page)
    await seedSession(page, buildSession('00000000-0000-0000-0000-000000000001', 'editor@example.com'))

    const manuscriptId = '00000000-0000-0000-0000-000000000302'
    const acceptedAssignmentId = 'ra-accepted'
    const invitedAssignmentId = 'ra-invited'
    let exitPayload: Record<string, unknown> | null = null

    const detailState = {
      id: manuscriptId,
      title: 'Review Stage Exit Manuscript',
      status: 'under_review',
      updated_at: '2026-03-10T12:00:00Z',
      created_at: '2026-03-10T10:00:00Z',
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
          id: invitedAssignmentId,
          reviewer_id: 'reviewer-invited',
          reviewer_name: 'Invited Reviewer',
          reviewer_email: 'invited@example.com',
          status: 'invited',
          round_number: 1,
          due_at: '2026-03-20T00:00:00Z',
          invited_at: '2026-03-10T10:05:00Z',
          opened_at: null,
          accepted_at: null,
          declined_at: null,
          last_reminded_at: null,
          submitted_at: null,
          latest_email_status: 'sent',
          latest_email_at: '2026-03-10T10:05:03Z',
          latest_email_error: null,
          email_events: [],
        },
        {
          id: acceptedAssignmentId,
          reviewer_id: 'reviewer-accepted',
          reviewer_name: 'Accepted Reviewer',
          reviewer_email: 'accepted@example.com',
          status: 'accepted',
          round_number: 1,
          due_at: '2026-03-21T00:00:00Z',
          invited_at: '2026-03-10T10:01:00Z',
          opened_at: '2026-03-10T10:10:00Z',
          accepted_at: '2026-03-10T10:12:00Z',
          declined_at: null,
          last_reminded_at: null,
          submitted_at: null,
          latest_email_status: 'sent',
          latest_email_at: '2026-03-10T10:01:03Z',
          latest_email_error: null,
          email_events: [],
        },
      ],
      author_response_history: [],
    }

    await page.route('**/api/v1/**', async (route) => {
      const req = route.request()
      const pathname = new URL(req.url()).pathname

      if (pathname === '/api/v1/cms/menu') {
        return fulfillJson(route, 200, { success: true, data: [] })
      }
      if (pathname === '/api/v1/user/profile') {
        return fulfillJson(route, 200, {
          success: true,
          data: { roles: ['admin', 'managing_editor', 'assistant_editor', 'editor_in_chief'] },
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
            roles: ['admin', 'managing_editor', 'assistant_editor', 'editor_in_chief'],
            normalized_roles: ['admin', 'managing_editor', 'assistant_editor', 'editor_in_chief'],
            allowed_actions: [
              'process:view',
              'manuscript:view_detail',
              'review:assign',
              'review:view_assignments',
              'review:unassign',
              'decision:record_first',
              'decision:submit_final',
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
        return fulfillJson(route, 200, { success: true, data: detailState })
      }
      if (pathname === `/api/v1/editor/manuscripts/${manuscriptId}/cards-context`) {
        return fulfillJson(route, 200, {
          success: true,
          data: {
            task_summary: detailState.task_summary,
            role_queue: {
              current_role: 'assistant_editor',
              current_assignee: { id: 'ae-1', full_name: 'AE User', email: 'ae@example.com' },
              current_assignee_label: null,
              assigned_at: '2026-03-10T10:00:00Z',
              technical_completed_at: null,
              academic_completed_at: null,
            },
          },
        })
      }
      if (pathname === `/api/v1/manuscripts/${manuscriptId}/reviews`) {
        return fulfillJson(route, 200, {
          success: true,
          data: [
            {
              id: 'report-1',
              reviewer_id: 'reviewer-completed',
              reviewer_name: 'Completed Reviewer',
              report_status: 'completed',
              comments_for_author: 'Good paper',
              confidential_comments_to_editor: 'Enough to decide',
              submitted_at: '2026-03-10T11:00:00Z',
            },
          ],
        })
      }
      if (pathname === `/api/v1/editor/manuscripts/${manuscriptId}/review-stage-exit` && req.method() === 'POST') {
        exitPayload = (req.postDataJSON() as Record<string, unknown>) || null
        detailState.status = 'decision'
        detailState.updated_at = '2026-03-10T12:05:00Z'
        detailState.reviewer_invites = detailState.reviewer_invites.map((invite) => {
          if (invite.id === invitedAssignmentId) {
            return {
              ...invite,
              status: 'cancelled',
              cancelled_at: '2026-03-10T12:05:00Z',
            }
          }
          if (invite.id === acceptedAssignmentId) {
            return {
              ...invite,
              status: 'cancelled',
              cancelled_at: '2026-03-10T12:05:00Z',
            }
          }
          return invite
        })
        return fulfillJson(route, 200, {
          success: true,
          data: {
            manuscript_status: 'decision',
            target_stage: 'first',
            auto_cancelled_assignment_ids: [invitedAssignmentId],
            manually_cancelled_assignment_ids: [acceptedAssignmentId],
            remaining_pending_assignment_ids: [],
            cancellation_email_sent_assignment_ids: [acceptedAssignmentId],
            cancellation_email_failed_assignment_ids: [],
          },
        })
      }

      if (pathname === '/api/v1/editor/academic-editors' && req.method() === 'GET') {
        return fulfillJson(route, 200, {
          success: true,
          data: [
            { id: 'academic-1', full_name: 'Academic Editor', email: 'academic@example.com' },
            { id: 'eic-1', full_name: 'Editor in Chief', email: 'chief@example.com' },
          ],
        })
      }

      return fulfillJson(route, 200, { success: true, data: [] })
    })

    await page.goto(`/editor/manuscript/${manuscriptId}`, { waitUntil: 'domcontentloaded' })

    await expect(page.getByRole('heading', { name: 'Review Stage Exit Manuscript' })).toBeVisible({ timeout: 15000 })
    await expect(page.getByRole('button', { name: /Exit Review Stage/i })).toBeVisible()
    await expect(page.getByText(/Decision Workspace 仅在 `decision \/ decision_done` 阶段开放/i)).toBeVisible()

    await page.getByRole('button', { name: /Exit Review Stage/i }).click()

    const exitDialog = page.getByRole('dialog')
    await expect(exitDialog).toBeVisible()
    await expect(exitDialog.getByText(/系统会自动 cancel 1 位 selected \/ invited \/ opened reviewer/i)).toBeVisible()
    await expect(exitDialog.getByText(/Accepted but not submitted/i)).toBeVisible()
    await expect(exitDialog.getByText('Accepted Reviewer', { exact: true })).toBeVisible()
    await expect(exitDialog.getByText(/AE recommendation for First Decision/i)).toBeVisible()
    await expect(exitDialog.getByLabel('First Decision recipients')).toHaveValue(
      'academic@example.com, chief@example.com'
    )

    await page.getByRole('button', { name: 'Continue' }).click()
    await expect(page.getByText(/Please explicitly handle every accepted reviewer/i)).toBeVisible()

    await page.getByRole('button', { name: 'Keep waiting' }).click()
    await page.getByRole('button', { name: 'Continue' }).click()
    await expect(page.getByText(/Some accepted reviewers are still marked as waiting/i)).toBeVisible()

    await page.getByRole('button', { name: 'Cancel reviewer' }).click()
    await page.getByPlaceholder('Explain why review stage is being closed and why any accepted reviewers are being cancelled...').fill(
      'Two completed reviews are enough for first decision.'
    )
    await page.getByRole('button', { name: 'Continue' }).click()

    await expect(page.getByText(/Moved manuscript to First Decision/i)).toBeVisible()
    await expect(page.getByRole('dialog')).toBeHidden()
    await expect(page.getByRole('button', { name: /Open Decision Workspace/i })).toBeVisible()

    expect(exitPayload).toEqual({
      target_stage: 'first',
      requested_outcome: 'major_revision',
      recipient_emails: ['academic@example.com', 'chief@example.com'],
      note: 'Two completed reviews are enough for first decision.',
      accepted_pending_resolutions: [
        {
          assignment_id: acceptedAssignmentId,
          action: 'cancel',
          reason: 'Two completed reviews are enough for first decision.',
        },
      ],
    })
  })

  ;([
    { targetStage: 'major_revision', label: 'Major Revision' },
    { targetStage: 'minor_revision', label: 'Minor Revision' },
  ] as const).forEach(({ targetStage, label }) => {
    test(`allows direct ${label.toLowerCase()} via Exit Review Stage`, async ({ page }) => {
      await enableE2EAuthBypass(page)
      await seedSession(page, buildSession('00000000-0000-0000-0000-000000000001', 'editor@example.com'))

      const manuscriptId = `00000000-0000-0000-0000-0000000003${targetStage === 'major_revision' ? '03' : '04'}`
      let exitPayload: Record<string, unknown> | null = null

      const detailState = {
        id: manuscriptId,
        title: `${label} Exit Manuscript`,
        status: 'under_review',
        updated_at: '2026-03-10T12:00:00Z',
        created_at: '2026-03-10T10:00:00Z',
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
        reviewer_invites: [],
        author_response_history: [],
      }

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
                'decision:record_first',
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
          return fulfillJson(route, 200, { success: true, data: detailState })
        }
        if (pathname === `/api/v1/editor/manuscripts/${manuscriptId}/cards-context`) {
          return fulfillJson(route, 200, {
            success: true,
            data: {
              task_summary: detailState.task_summary,
              role_queue: {
                current_role: 'assistant_editor',
                current_assignee: { id: 'ae-1', full_name: 'AE User', email: 'ae@example.com' },
                current_assignee_label: null,
                assigned_at: '2026-03-10T10:00:00Z',
                technical_completed_at: null,
                academic_completed_at: null,
              },
            },
          })
        }
        if (pathname === `/api/v1/manuscripts/${manuscriptId}/reviews`) {
          return fulfillJson(route, 200, { success: true, data: [] })
        }
        if (pathname === `/api/v1/editor/manuscripts/${manuscriptId}/review-stage-exit` && req.method() === 'POST') {
          exitPayload = (req.postDataJSON() as Record<string, unknown>) || null
          detailState.status = targetStage
          detailState.updated_at = '2026-03-10T12:05:00Z'
          return fulfillJson(route, 200, {
            success: true,
            data: {
              manuscript_status: targetStage,
              target_stage: targetStage,
              auto_cancelled_assignment_ids: [],
              manually_cancelled_assignment_ids: [],
              remaining_pending_assignment_ids: [],
              cancellation_email_sent_assignment_ids: [],
              cancellation_email_failed_assignment_ids: [],
              author_revision_email_failed_recipient: null,
            },
          })
        }

        return fulfillJson(route, 200, { success: true, data: [] })
      })

      await page.goto(`/editor/manuscript/${manuscriptId}`, { waitUntil: 'domcontentloaded' })

      await expect(page.getByRole('heading', { name: `${label} Exit Manuscript` })).toBeVisible({ timeout: 15000 })
      await page.getByRole('button', { name: /Exit Review Stage/i }).click()

      const exitDialog = page.getByRole('dialog')
      await expect(exitDialog).toBeVisible()
      await page
        .getByRole('radio', { name: new RegExp(`Direct\\s+${label}`, 'i') })
        .click()
      await page
        .getByPlaceholder('Explain why review stage is being closed and why any accepted reviewers are being cancelled...')
        .fill(`Move directly to ${label}.`)
      await page.getByRole('button', { name: 'Continue' }).click()

      await expect(page.getByText(new RegExp(`Moved manuscript to ${label}`, 'i'))).toBeVisible()
      await expect(page.getByRole('button', { name: /Exit Review Stage/i })).toBeHidden()

      expect(exitPayload).toEqual({
        target_stage: targetStage,
        note: `Move directly to ${label}.`,
        accepted_pending_resolutions: [],
      })
    })
  })
})
