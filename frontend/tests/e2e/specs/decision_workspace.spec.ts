import { expect, test } from '@playwright/test'
import { buildSession, fulfillJson, seedSession } from '../utils'

test.describe('Decision Workspace flow (mocked)', () => {
  test('supports draft and final decision submission', async ({ page }) => {
    const manuscriptId = '00000000-0000-0000-0000-000000009999'
    await page.context().setExtraHTTPHeaders({ 'x-scholarflow-e2e': '1' })
    await seedSession(page, buildSession('11111111-1111-1111-1111-111111111111', 'editor@example.com'))

    const decisionPayloads: any[] = []

    await page.route('**/api/v1/**', async (route) => {
      const req = route.request()
      const pathname = new URL(req.url()).pathname

      if (pathname === `/api/v1/editor/manuscripts/${manuscriptId}/decision-context`) {
        return fulfillJson(route, 200, {
          success: true,
          data: {
            manuscript: {
              id: manuscriptId,
              title: 'Decision Workspace Mock Manuscript',
              abstract: 'Mock abstract',
              status: 'decision',
              version: 2,
              pdf_url: 'https://example.com/mock.pdf',
            },
            reports: [
              {
                id: 'r-1',
                reviewer_id: 'rv-1',
                reviewer_name: 'Reviewer One',
                status: 'completed',
                score: 4,
                comments_for_author: 'Please add stronger experiment analysis.',
                confidential_comments_to_editor: 'Overall solid paper.',
                attachment: null,
              },
            ],
            draft: null,
            templates: [{ id: 'default', name: 'Default', content: 'Template from backend' }],
            permissions: { can_submit: true, is_read_only: false },
          },
        })
      }

      if (pathname === `/api/v1/editor/manuscripts/${manuscriptId}/decision-attachments` && req.method() === 'POST') {
        return fulfillJson(route, 200, {
          success: true,
          data: {
            attachment_id: 'att-1',
            path: `decision_letters/${manuscriptId}/att-1_demo.pdf`,
            ref: `att-1|decision_letters/${manuscriptId}/att-1_demo.pdf`,
          },
        })
      }

      if (pathname === `/api/v1/editor/manuscripts/${manuscriptId}/submit-decision` && req.method() === 'POST') {
        const body = req.postDataJSON()
        decisionPayloads.push(body)
        return fulfillJson(route, 200, {
          success: true,
          data: {
            decision_letter_id: 'dl-1',
            status: body?.is_final ? 'final' : 'draft',
            manuscript_status: body?.is_final ? 'approved' : 'decision',
            updated_at: new Date().toISOString(),
          },
        })
      }

      return route.fulfill({ status: 404, body: 'not mocked' })
    })

    await page.goto(`/editor/decision/${manuscriptId}`)

    await expect(page.getByText('Final Decision Workspace')).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Decision Workspace Mock Manuscript' })).toBeVisible()
    await expect(page.getByText('Review Reports')).toBeVisible()
    await expect(page.getByText('Decision Letter')).toBeVisible()

    await page.getByRole('button', { name: 'Generate Letter Draft' }).click()
    await page.getByRole('button', { name: 'Save Draft' }).click()
    await page.getByRole('button', { name: 'Submit Final Decision' }).click()

    await expect.poll(() => decisionPayloads.length).toBe(2)
    expect(decisionPayloads[0]?.is_final).toBe(false)
    expect(decisionPayloads[1]?.is_final).toBe(true)
  })
})
