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

      if (pathname === '/api/v1/editor/assistant-editors') {
        return fulfillJson(route, 200, {
          success: true,
          data: [{ id: aeId, full_name: 'Alice Editor', email: 'alice@example.com' }],
        })
      }

      if (pathname === '/api/v1/editor/intake' && req.method() === 'GET') {
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

      if (pathname === '/api/v1/editor/workspace' && req.method() === 'GET') {
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

      if (pathname === '/api/v1/editor/academic' && req.method() === 'GET') {
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
    await expect(page.getByText('Mocked Precheck Manuscript')).toBeVisible()
    await page.getByRole('button', { name: 'Assign AE' }).click()
    await expect(page.getByRole('heading', { name: 'Assign Assistant Editor' })).toBeVisible()
    await page.locator('select').selectOption(aeId)
    await page.getByRole('button', { name: 'Assign', exact: true }).click()

    // 2) AE Workspace -> submit pass
    await page.goto('/editor/workspace')
    await expect(page.getByRole('heading', { name: 'Assistant Editor Workspace' })).toBeVisible()
    await expect(page.getByText('Mocked Precheck Manuscript')).toBeVisible()
    await page.getByRole('button', { name: 'Submit Check' }).click()
    await page.getByRole('button', { name: 'Confirm' }).click()

    // 3) EIC Academic -> send to review
    await page.goto('/editor/academic')
    await expect(page.getByRole('heading', { name: 'EIC Academic Pre-check Queue' })).toBeVisible()
    await expect(page.getByText('Mocked Precheck Manuscript')).toBeVisible()
    await page.getByRole('button', { name: 'Make Decision' }).click()
    await page.getByLabel('Send to External Review').check()
    await page.getByRole('button', { name: 'Submit' }).click()
  })
})
