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
      if (pathname.includes('/api/v1/editor/manuscripts/process')) {
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
      if (pathname.includes('/api/v1/editor/manuscripts/process')) {
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

    await page.goto('/editor/process?q=scope-cross-journal')
    await expect(page).toHaveURL(/q=scope-cross-journal/)
    await expect(page.getByRole('columnheader', { name: 'Actions' })).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Bind' })).toHaveCount(0)

    const rejected = await page.evaluate(async (id) => {
      const res = await fetch(`/api/v1/editor/manuscripts/${id}/bind-owner`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ owner_id: 'owner-1' }),
      })
      return { status: res.status, body: await res.json() }
    }, manuscriptId)

    expect(rejected.status).toBe(403)
    expect(String((rejected.body as { detail?: string }).detail || '')).toContain('Forbidden by journal scope')
  })

  test('assistant editor can access workspace within scoped assignments', async ({ page }) => {
    await enableE2EAuthBypass(page)
    await seedSession(page, buildSession('cccccccc-cccc-cccc-cccc-cccccccccccc', 'assistant@example.com'))

    await page.route('**/api/v1/**', async (route) => {
      const req = route.request()
      const pathname = new URL(req.url()).pathname

      if (pathname === '/api/v1/user/profile') {
        return fulfillJson(route, 200, { success: true, data: { roles: ['assistant_editor'] } })
      }
      if (pathname.startsWith('/api/v1/editor/workspace')) {
        return fulfillJson(route, 200, [
          {
            id: 'ms-technical-1',
            title: 'Scoped Workspace Manuscript',
            status: 'pre_check',
            pre_check_status: 'technical',
            updated_at: new Date().toISOString(),
            created_at: new Date().toISOString(),
            owner: { id: 'owner-1', full_name: 'Owner One', email: 'owner@example.com' },
            journal: { title: 'Scoped Journal', slug: 'scoped-journal' },
          },
        ])
      }
      if (pathname.includes('/submit-check') && req.method() === 'POST') {
        return fulfillJson(route, 200, { success: true, message: 'ok' })
      }

      return fulfillJson(route, 200, { success: true, data: {} })
    })

    await page.goto('/editor/workspace')
    await expect(page.getByRole('heading', { name: 'Assistant Editor Workspace' })).toBeVisible()
    const refreshResponse = page.waitForResponse(
      (res) => res.url().includes('/api/v1/editor/workspace') && res.request().method() === 'GET'
    )
    await page.getByTestId('workspace-refresh-btn').click()
    await refreshResponse
    await expect(page.getByText('Scoped Workspace Manuscript')).toBeVisible({ timeout: 15_000 })
    await expect(page.getByRole('button', { name: 'Submit Check' })).toBeVisible()
  })
})
