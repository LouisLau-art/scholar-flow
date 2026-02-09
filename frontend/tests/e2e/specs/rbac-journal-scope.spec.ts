import { expect, test } from '@playwright/test'

import { buildSession, fulfillJson, seedSession } from '../utils'

async function enableE2EAuthBypass(page: import('@playwright/test').Page) {
  await page.context().setExtraHTTPHeaders({ 'x-scholarflow-e2e': '1' })
}

test.describe('RBAC journal scope (mocked)', () => {
  test('shows scope hint and scoped empty state', async ({ page }) => {
    await enableE2EAuthBypass(page)
    await seedSession(page, buildSession('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'me@example.com'))

    await page.route('**/api/v1/**', async (route) => {
      const req = route.request()
      const pathname = new URL(req.url()).pathname

      if (pathname === '/api/v1/user/profile') {
        return fulfillJson(route, 200, { success: true, data: { roles: ['managing_editor'] } })
      }
      if (pathname === '/api/v1/editor/rbac/context') {
        return fulfillJson(route, 200, {
          success: true,
          data: {
            user_id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
            roles: ['managing_editor'],
            normalized_roles: ['managing_editor'],
            allowed_actions: ['process:view'],
            journal_scope: {
              enforcement_enabled: true,
              allowed_journal_ids: [],
              is_admin: false,
            },
          },
        })
      }
      if (pathname === '/api/v1/editor/manuscripts/process') {
        return fulfillJson(route, 200, { success: true, data: [] })
      }
      if (pathname === '/api/v1/editor/journals') return fulfillJson(route, 200, { success: true, data: [] })
      if (pathname === '/api/v1/editor/internal-staff') return fulfillJson(route, 200, { success: true, data: [] })

      return fulfillJson(route, 200, { success: true, data: {} })
    })

    await page.goto('/editor/process')
    await expect(page.getByText('Scope enabled: no journal is assigned to your role yet.')).toBeVisible()
    await expect(page.getByText('No manuscript in your assigned journal scope.')).toBeVisible()
  })

  test('shows backend 403 when cross-journal write is rejected', async ({ page }) => {
    await enableE2EAuthBypass(page)
    await seedSession(page, buildSession('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'eic@example.com'))

    const manuscriptId = '11111111-1111-1111-1111-111111111111'
    await page.route('**/api/v1/**', async (route) => {
      const req = route.request()
      const pathname = new URL(req.url()).pathname

      if (pathname === '/api/v1/user/profile') {
        return fulfillJson(route, 200, { success: true, data: { roles: ['editor_in_chief'] } })
      }
      if (pathname === '/api/v1/editor/rbac/context') {
        return fulfillJson(route, 200, {
          success: true,
          data: {
            user_id: 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
            roles: ['editor_in_chief'],
            normalized_roles: ['editor_in_chief'],
            allowed_actions: ['process:view', 'manuscript:view_detail', 'manuscript:bind_owner'],
            journal_scope: {
              enforcement_enabled: true,
              allowed_journal_ids: ['j-allowed'],
              is_admin: false,
            },
          },
        })
      }
      if (pathname === '/api/v1/editor/manuscripts/process') {
        return fulfillJson(route, 200, {
          success: true,
          data: [
            {
              id: manuscriptId,
              title: 'Cross Journal Manuscript',
              status: 'under_review',
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
              journals: { title: 'Forbidden Journal', slug: 'forbidden' },
              owner: null,
              editor: null,
            },
          ],
        })
      }
      if (pathname === '/api/v1/editor/internal-staff') {
        return fulfillJson(route, 200, {
          success: true,
          data: [{ id: 'owner-1', full_name: 'Owner One', email: 'owner@example.com' }],
        })
      }
      if (pathname === `/api/v1/editor/manuscripts/${manuscriptId}/bind-owner` && req.method() === 'POST') {
        return fulfillJson(route, 403, { success: false, detail: 'Forbidden by journal scope' })
      }
      if (pathname === '/api/v1/editor/journals') return fulfillJson(route, 200, { success: true, data: [] })

      return fulfillJson(route, 200, { success: true, data: {} })
    })

    await page.goto('/editor/process')
    await expect(page.getByText(manuscriptId)).toBeVisible()

    await page.getByRole('button', { name: 'Bind' }).click()
    await expect(page.getByRole('heading', { name: 'Bind Internal Owner' })).toBeVisible()
    await page.getByRole('button', { name: 'Select' }).click()

    await expect(page.getByText('Forbidden by journal scope')).toBeVisible()
  })
})
