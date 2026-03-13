import { test, expect } from '@playwright/test'
import { buildSession, fulfillJson, seedSession } from '../utils'

async function enableE2EAuthBypass(page: import('@playwright/test').Page) {
  await page.context().setExtraHTTPHeaders({ 'x-scholarflow-e2e': '1' })
}

test.describe('Production workflow (mocked backend)', () => {
  test('Editor views production card and can open workspace', async ({ page }) => {
    await enableE2EAuthBypass(page)
    await seedSession(page, buildSession('00000000-0000-0000-0000-000000000123', 'editor@example.com'))

    const manuscriptId = '00000000-0000-0000-0000-000000000456'

    await page.route('**/api/v1/**', async (route) => {
      const pathname = new URL(route.request().url()).pathname

      if (pathname === '/api/v1/user/profile') {
        return fulfillJson(route, 200, { success: true, data: { roles: ['managing_editor'] } })
      }
      if (pathname === '/api/v1/editor/rbac/context') {
        return fulfillJson(route, 200, {
          success: true,
          data: {
            user_id: '00000000-0000-0000-0000-000000000123',
            roles: ['managing_editor'],
            normalized_roles: ['managing_editor'],
            allowed_actions: ['manuscript:view_detail', 'decision:record_first', 'decision:submit_final'],
            journal_scope: { enforcement_enabled: false, allowed_journal_ids: [], is_admin: true },
          },
        })
      }
      if (pathname.startsWith('/api/v1/cms/menu')) return fulfillJson(route, 200, { success: true, data: [] })

      if (pathname === `/api/v1/editor/manuscripts/${manuscriptId}`) {
        return fulfillJson(route, 200, {
          success: true,
          data: {
            id: manuscriptId,
            title: 'Mocked Production Manuscript',
            status: 'approved',
            invoice: { status: 'paid', amount: 1000 },
          }
        })
      }

      if (pathname.includes('/versions')) return fulfillJson(route, 200, { success: true, data: [] })
      if (pathname.includes('/comments')) return fulfillJson(route, 200, { success: true, data: [] })
      if (pathname.includes('/tasks')) return fulfillJson(route, 200, { success: true, data: [] })
      if (pathname.includes('/audit-logs')) return fulfillJson(route, 200, { success: true, data: [] })
      if (pathname.includes('/timeline-context')) return fulfillJson(route, 200, { success: true, data: { events: [] } })
      if (pathname.includes('/cards-context')) return fulfillJson(route, 200, { success: true, data: { task_summary: {}, role_queue: {} } })

      return fulfillJson(route, 200, { success: true, data: {} })
    })

    await page.goto(`/editor/manuscript/${manuscriptId}`)

    await expect(page.getByTestId('production-status-card')).toBeVisible()
    await expect(page.getByTestId('production-stage')).toHaveText('Accepted')
    
    // Direct advance buttons are gone, now it only has the workspace link
    await expect(page.getByRole('link', { name: 'Open Production Workspace' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Start Layout' })).not.toBeVisible()
  })


  test('Publish lives in workspace and shows friendly payment error', async ({ page }) => {
    await enableE2EAuthBypass(page)
    await seedSession(page, buildSession('00000000-0000-0000-0000-000000000123', 'editor@example.com'))

    const manuscriptId = '00000000-0000-0000-0000-000000000789'

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
            user_id: '00000000-0000-0000-0000-000000000123',
            roles: ['managing_editor'],
            normalized_roles: ['managing_editor'],
            allowed_actions: ['manuscript:view_detail', 'decision:record_first', 'decision:submit_final'],
            journal_scope: { enforcement_enabled: false, allowed_journal_ids: [], is_admin: true },
          },
        })
      }
      if (pathname.startsWith('/api/v1/cms/menu')) return fulfillJson(route, 200, { success: true, data: [] })

      if (pathname === `/api/v1/editor/manuscripts/${manuscriptId}`) {
        return fulfillJson(route, 200, {
          success: true,
          data: {
            id: manuscriptId,
            title: 'Mocked Publish Gate Manuscript',
            status: 'approved_for_publish',
            final_pdf_path: `production/${manuscriptId}/final.pdf`,
            invoice: { status: 'unpaid', amount: 1000 },
          }
        })
      }

      if (pathname === `/api/v1/editor/manuscripts/${manuscriptId}/production-workspace`) {
        return fulfillJson(route, 200, {
          success: true,
          data: {
            manuscript: {
              id: manuscriptId,
              title: 'Mocked Publish Gate Manuscript',
              status: 'approved_for_publish',
              author_id: '00000000-0000-0000-0000-000000000999',
              pdf_url: 'https://example.com/proof.pdf',
            },
            active_cycle: {
              id: 'cycle-1',
              manuscript_id: manuscriptId,
              cycle_no: 1,
              status: 'approved_for_publish',
              stage: 'ready_to_publish',
              layout_editor_id: '00000000-0000-0000-0000-000000000123',
              proofreader_author_id: '00000000-0000-0000-0000-000000000999',
              galley_path: `production_cycles/${manuscriptId}/cycle-1/proof.pdf`,
              artifacts: [],
            },
            cycle_history: [],
            permissions: {
              can_create_cycle: false,
              can_manage_editors: true,
              can_upload_galley: true,
              can_approve: true,
            },
          },
        })
      }

      if (pathname === '/api/v1/editor/internal-staff') {
        return fulfillJson(route, 200, { success: true, data: [] })
      }

      if (pathname === `/api/v1/editor/manuscripts/${manuscriptId}/production/advance` && req.method() === 'POST') {
        return fulfillJson(route, 403, { detail: 'Payment Required: Invoice is unpaid.' })
      }

      if (pathname.includes('/versions')) return fulfillJson(route, 200, { success: true, data: [] })
      if (pathname.includes('/comments')) return fulfillJson(route, 200, { success: true, data: [] })
      if (pathname.includes('/tasks')) return fulfillJson(route, 200, { success: true, data: [] })
      if (pathname.includes('/audit-logs')) return fulfillJson(route, 200, { success: true, data: [] })
      if (pathname.includes('/timeline-context')) return fulfillJson(route, 200, { success: true, data: { events: [] } })
      if (pathname.includes('/cards-context')) return fulfillJson(route, 200, { success: true, data: { task_summary: {}, role_queue: {} } })

      return fulfillJson(route, 200, { success: true, data: {} })
    })

      await page.goto(`/editor/manuscript/${manuscriptId}`)

      await expect(page.getByTestId('production-stage')).toHaveText('approved_for_publish')
      await expect(page.getByRole('button', { name: 'Publish Manuscript' })).toHaveCount(0)
      await page.goto(`/editor/production/${manuscriptId}`)
      await page.getByRole('button', { name: 'Publish Manuscript' }).click()
      await expect(page.getByText('Waiting for Payment.')).toBeVisible()
    })
  })
