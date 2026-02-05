import { test, expect } from '@playwright/test'
import { buildSession, fulfillJson, seedSession } from '../utils'

async function enableE2EAuthBypass(page: import('@playwright/test').Page) {
  await page.context().setExtraHTTPHeaders({ 'x-scholarflow-e2e': '1' })
}

test.describe('Production workflow (mocked backend)', () => {
  test('Editor advances stages and can revert', async ({ page }) => {
    await enableE2EAuthBypass(page)
    await seedSession(page, buildSession('00000000-0000-0000-0000-000000000123', 'editor@example.com'))

    const manuscriptId = '00000000-0000-0000-0000-000000000456'
    let status = 'approved'

    const buildDetail = () => ({
      id: manuscriptId,
      title: 'Mocked Production Manuscript',
      abstract: 'Mocked abstract',
      status,
      final_pdf_path: `production/${manuscriptId}/final.pdf`,
      invoice: { status: 'paid', amount: 1000 },
      signed_files: {
        original_manuscript: { signed_url: 'https://example.com/final.pdf', path: 'mock/path.pdf' },
        peer_review_reports: [],
      },
      invoice_metadata: { authors: 'A', affiliation: 'B', apc_amount: 1000, funding_info: '' },
    })

    const nextOf: Record<string, string> = {
      approved: 'layout',
      layout: 'english_editing',
      english_editing: 'proofreading',
      proofreading: 'published',
    }
    const prevOf: Record<string, string> = {
      layout: 'approved',
      english_editing: 'layout',
      proofreading: 'english_editing',
    }

    await page.route('**/api/v1/**', async (route) => {
      const req = route.request()
      const url = new URL(req.url())
      const pathname = url.pathname

      if (pathname === '/api/v1/user/profile') {
        return fulfillJson(route, 200, { success: true, data: { roles: ['editor'] } })
      }

      if (pathname.startsWith('/api/v1/cms/menu')) {
        return fulfillJson(route, 200, { success: true, data: [] })
      }

      if (pathname === `/api/v1/editor/manuscripts/${manuscriptId}`) {
        return fulfillJson(route, 200, { success: true, data: buildDetail() })
      }

      if (pathname === `/api/v1/editor/manuscripts/${manuscriptId}/production/advance` && req.method() === 'POST') {
        status = nextOf[status] ?? status
        return fulfillJson(route, 200, {
          success: true,
          data: { previous_status: 'x', new_status: status, manuscript: { id: manuscriptId, status } },
        })
      }

      if (pathname === `/api/v1/editor/manuscripts/${manuscriptId}/production/revert` && req.method() === 'POST') {
        status = prevOf[status] ?? status
        return fulfillJson(route, 200, {
          success: true,
          data: { previous_status: 'x', new_status: status, manuscript: { id: manuscriptId, status } },
        })
      }

      // VersionHistory / misc endpoints used by the page
      if (pathname.includes('/versions')) {
        return fulfillJson(route, 200, { success: true, data: [] })
      }

      return route.fallback()
    })

    await page.goto(`/editor/manuscript/${manuscriptId}`)

    await expect(page.getByTestId('production-status-card')).toBeVisible()
    await expect(page.getByTestId('production-stage')).toHaveText('Accepted')

    await page.getByRole('button', { name: 'Start Layout' }).click()
    await expect(page.getByTestId('production-stage')).toHaveText('Layout')

    await page.getByRole('button', { name: 'Start English Editing' }).click()
    await expect(page.getByTestId('production-stage')).toHaveText('English Editing')

    await page.getByRole('button', { name: 'Revert' }).click()
    await expect(page.getByTestId('production-stage')).toHaveText('Layout')
  })

  test('Publish shows friendly payment error', async ({ page }) => {
    await enableE2EAuthBypass(page)
    await seedSession(page, buildSession('00000000-0000-0000-0000-000000000123', 'editor@example.com'))

    const manuscriptId = '00000000-0000-0000-0000-000000000789'
    let status = 'proofreading'

    await page.route('**/api/v1/**', async (route) => {
      const req = route.request()
      const url = new URL(req.url())
      const pathname = url.pathname

      if (pathname === '/api/v1/user/profile') {
        return fulfillJson(route, 200, { success: true, data: { roles: ['editor'] } })
      }

      if (pathname.startsWith('/api/v1/cms/menu')) {
        return fulfillJson(route, 200, { success: true, data: [] })
      }

      if (pathname === `/api/v1/editor/manuscripts/${manuscriptId}`) {
        return fulfillJson(route, 200, {
          success: true,
          data: {
            id: manuscriptId,
            title: 'Mocked Publish Gate Manuscript',
            status,
            final_pdf_path: `production/${manuscriptId}/final.pdf`,
            invoice: { status: 'unpaid', amount: 1000 },
            signed_files: { original_manuscript: { signed_url: 'https://example.com/final.pdf' }, peer_review_reports: [] },
          },
        })
      }

      if (pathname === `/api/v1/editor/manuscripts/${manuscriptId}/production/advance` && req.method() === 'POST') {
        return fulfillJson(route, 403, { detail: 'Payment Required: Invoice is unpaid.' })
      }

      if (pathname.includes('/versions')) {
        return fulfillJson(route, 200, { success: true, data: [] })
      }

      return route.fallback()
    })

    await page.goto(`/editor/manuscript/${manuscriptId}`)

    await expect(page.getByTestId('production-stage')).toHaveText('Proofreading')
    await page.getByRole('button', { name: 'Publish' }).click()
    await expect(page.getByText('Waiting for Payment.')).toBeVisible()
  })
})
