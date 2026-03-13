import { test, expect } from '@playwright/test'
import { buildSession, fulfillJson, seedSession } from '../utils'

async function enableE2EAuthBypass(page: import('@playwright/test').Page) {
  await page.context().setExtraHTTPHeaders({ 'x-scholarflow-e2e': '1' })
}

test.describe('Publish workflow (mocked backend)', () => {
  test('Editor publishes from production workspace when gates are ready', async ({ page }) => {
    await enableE2EAuthBypass(page)
    await seedSession(page, buildSession('00000000-0000-0000-0000-000000000123', 'editor@example.com'))

    const manuscriptId = '00000000-0000-0000-0000-000000000456'

    let workspaceContext: any = {
      manuscript: {
        id: manuscriptId,
        title: 'Mocked Post-Acceptance Manuscript',
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
    }

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

      if (pathname === `/api/v1/editor/manuscripts/${manuscriptId}/production-workspace`) {
        return fulfillJson(route, 200, { success: true, data: workspaceContext })
      }

      if (pathname === '/api/v1/editor/internal-staff') {
        return fulfillJson(route, 200, { success: true, data: [] })
      }

      if (pathname === `/api/v1/editor/manuscripts/${manuscriptId}/production/advance` && req.method() === 'POST') {
        workspaceContext = {
          ...workspaceContext,
          manuscript: {
            ...workspaceContext.manuscript,
            status: 'published',
          },
        }
        return fulfillJson(route, 200, { success: true, data: { new_status: 'published' } })
      }

      return fulfillJson(route, 200, { success: true, data: {} })
    })

    await page.goto(`/editor/production/${manuscriptId}`)
    await expect(page.getByRole('button', { name: 'Publish Manuscript' })).toBeVisible()
    await page.getByRole('button', { name: 'Publish Manuscript' }).click()
    await expect(page.getByText('Moved to Published')).toBeVisible()
    await expect(page.getByText('Current status: published')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Publish Manuscript' })).toHaveCount(0)
  })
})
