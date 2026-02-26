import { expect, test } from '@playwright/test'

import { buildSession, fulfillJson, seedSession } from '../utils'

async function enableE2EAuthBypass(page: import('@playwright/test').Page) {
  await page.context().setExtraHTTPHeaders({ 'x-scholarflow-e2e': '1' })
}

test.describe('Pre-check workflow (mocked)', () => {
  test('ME -> AE -> EIC full path', async ({ page }) => {
    await enableE2EAuthBypass(page)
    await seedSession(page, buildSession('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'editor@example.com'))

    const manuscriptId = '55555555-5555-5555-5555-555555555555'
    const aeId = '66666666-6666-6666-6666-666666666666'
    let stage: 'intake' | 'technical' | 'academic' | 'done' = 'intake'

    await page.route('**/api/v1/**', async (route) => {
      const req = route.request()
      const url = new URL(req.url())
      const pathname = url.pathname

      if (pathname === '/api/v1/user/profile') {
        return fulfillJson(route, 200, {
          success: true,
          data: { roles: ['admin', 'managing_editor', 'assistant_editor', 'editor_in_chief'] },
        })
      }
      if (pathname === '/api/v1/editor/rbac/context') {
        return fulfillJson(route, 200, {
          success: true,
          data: {
            user_id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
            roles: ['admin', 'managing_editor', 'assistant_editor', 'editor_in_chief'],
            normalized_roles: ['admin', 'managing_editor', 'assistant_editor', 'editor_in_chief'],
            allowed_actions: ['process:view', 'manuscript:view_detail', 'decision:record_first', 'decision:submit_final'],
            journal_scope: { enforcement_enabled: false, allowed_journal_ids: [], is_admin: true },
          },
        })
      }
      if (pathname.startsWith('/api/v1/editor/internal-staff')) {
        return fulfillJson(route, 200, {
          success: true,
          data: [{ id: 'owner-1', full_name: 'Owner One', email: 'owner@example.com', roles: ['owner'] }],
        })
      }

      if (pathname === '/api/v1/editor/assistant-editors') {
        return fulfillJson(route, 200, {
          success: true,
          data: [{ id: aeId, full_name: 'Alice Editor', email: 'alice@example.com' }],
        })
      }

      if (pathname.startsWith('/api/v1/editor/intake') && req.method() === 'GET') {
        const data =
          stage === 'intake'
            ? [
                {
                  id: manuscriptId,
                  title: 'Mocked Precheck Manuscript',
                  status: 'pre_check',
                  pre_check_status: 'intake',
                },
              ]
            : []
        return fulfillJson(route, 200, data)
      }

      if (pathname === `/api/v1/editor/manuscripts/${manuscriptId}/assign-ae` && req.method() === 'POST') {
        stage = 'technical'
        return fulfillJson(route, 200, {
          message: 'AE assigned successfully',
          data: {
            id: manuscriptId,
            status: 'pre_check',
            pre_check_status: 'technical',
            assistant_editor_id: aeId,
          },
        })
      }

      if (pathname.startsWith('/api/v1/editor/workspace') && req.method() === 'GET') {
        const data =
          stage === 'technical'
            ? [
                {
                  id: manuscriptId,
                  title: 'Mocked Precheck Manuscript',
                  status: 'pre_check',
                  pre_check_status: 'technical',
                  assistant_editor_id: aeId,
                },
              ]
            : []
        return fulfillJson(route, 200, data)
      }

      if (pathname === `/api/v1/editor/manuscripts/${manuscriptId}/submit-check` && req.method() === 'POST') {
        const body = (await req.postDataJSON()) as any
        if (body?.decision === 'revision') {
          stage = 'done'
          return fulfillJson(route, 200, {
            message: 'Technical check submitted',
            data: {
              id: manuscriptId,
              status: 'minor_revision',
            },
          })
        }
        if (body?.decision === 'academic') {
          stage = 'academic'
          return fulfillJson(route, 200, {
            message: 'Technical check submitted',
            data: {
              id: manuscriptId,
              status: 'pre_check',
              pre_check_status: 'academic',
              assistant_editor_id: aeId,
            },
          })
        }
        stage = 'done'
        return fulfillJson(route, 200, {
          message: 'Technical check submitted',
          data: {
            id: manuscriptId,
            status: 'under_review',
          },
        })
      }

      if (pathname.startsWith('/api/v1/editor/academic') && req.method() === 'GET') {
        const data =
          stage === 'academic'
            ? [
                {
                  id: manuscriptId,
                  title: 'Mocked Precheck Manuscript',
                  status: 'pre_check',
                  pre_check_status: 'academic',
                },
              ]
            : []
        return fulfillJson(route, 200, data)
      }

      if (pathname === '/api/v1/editor/final-decision' && req.method() === 'GET') {
        return fulfillJson(route, 200, [])
      }

      if (pathname === `/api/v1/editor/manuscripts/${manuscriptId}/academic-check` && req.method() === 'POST') {
        stage = 'done'
        return fulfillJson(route, 200, {
          message: 'Academic check submitted',
          data: {
            id: manuscriptId,
            status: 'under_review',
          },
        })
      }

      return fulfillJson(route, 200, { success: true, data: {} })
    })

    // 1) ME Intake -> assign AE
    await page.goto('/editor/intake')
    await expect(page.getByRole('heading', { name: 'Managing Editor Intake Queue' })).toBeVisible()
    await page.getByPlaceholder('搜索标题 / UUID / 作者 / 期刊').fill('precheck-e2e')
    await page.getByRole('button', { name: '搜索' }).click()
    await expect(page.getByRole('button', { name: '通过并分配 AE' })).toBeVisible()
    await page.getByRole('button', { name: '通过并分配 AE' }).click()
    await expect(page.getByRole('heading', { name: 'Assign Assistant Editor' })).toBeVisible()
    await page.getByRole('combobox').first().click()
    await page.getByRole('option', { name: 'Alice Editor' }).click()
    await page.getByRole('button', { name: 'Assign', exact: true }).click()

    // 2) AE Workspace -> submit academic (optional pre-check path)
    await page.goto('/editor/workspace')
    await expect(page.getByRole('heading', { name: 'Assistant Editor Workspace' })).toBeVisible()
    await page.getByTestId('workspace-refresh-btn').click()
    await expect(page.getByText('Mocked Precheck Manuscript')).toBeVisible()
    await page.getByRole('button', { name: 'Submit Check' }).click()
    await page.getByRole('dialog').getByRole('combobox').click()
    await page.getByRole('option', { name: '送 Academic 预审（可选）' }).click()
    await page.getByRole('dialog').getByRole('button', { name: 'Confirm' }).click()

    // 3) EIC Academic -> send to review
    await page.goto('/editor/academic')
    await expect(page.getByRole('heading', { name: 'Editor-in-Chief Workspace' })).toBeVisible()
    await expect(page.getByText('Mocked Precheck Manuscript')).toBeVisible()
    await page.getByRole('button', { name: 'Make Decision' }).click()
    await page.getByLabel('Send to External Review').check()
    await page.getByRole('button', { name: 'Submit' }).click()
  })
})
