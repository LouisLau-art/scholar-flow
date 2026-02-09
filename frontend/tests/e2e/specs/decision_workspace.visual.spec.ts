import { expect, test } from '@playwright/test'
import { buildSession, fulfillJson, seedSession } from '../utils'

test.describe('Decision Workspace visual layout (mocked)', () => {
  test('renders immersive layout without global footer chrome', async ({ page }) => {
    const manuscriptId = '00000000-0000-0000-0000-000000008888'
    await page.context().setExtraHTTPHeaders({ 'x-scholarflow-e2e': '1' })
    await seedSession(page, buildSession('11111111-1111-1111-1111-111111111111', 'editor@example.com'))

    await page.route('**/api/v1/**', async (route) => {
      const pathname = new URL(route.request().url()).pathname
      if (pathname === `/api/v1/editor/manuscripts/${manuscriptId}/decision-context`) {
        return fulfillJson(route, 200, {
          success: true,
          data: {
            manuscript: {
              id: manuscriptId,
              title: 'Immersive Decision Workspace',
              status: 'decision',
              pdf_url: 'https://example.com/mock.pdf',
            },
            reports: [
              {
                id: 'r-1',
                reviewer_name: 'Reviewer One',
                status: 'completed',
                comments_for_author: 'Looks good after revision.',
                confidential_comments_to_editor: 'Can accept.',
              },
            ],
            draft: null,
            templates: [{ id: 'default', name: 'Default', content: 'Template content' }],
            permissions: { can_submit: true, is_read_only: false },
          },
        })
      }
      if (pathname === `/api/v1/editor/manuscripts/${manuscriptId}/submit-decision`) {
        return fulfillJson(route, 200, {
          success: true,
          data: {
            decision_letter_id: 'dl-1',
            status: 'draft',
            manuscript_status: 'decision',
            updated_at: new Date().toISOString(),
          },
        })
      }
      return route.fulfill({ status: 404, body: 'not mocked' })
    })

    await page.goto(`/editor/decision/${manuscriptId}`)

    await expect(page.getByText('Final Decision Workspace')).toBeVisible()
    await expect(page.getByText('Review Reports')).toBeVisible()
    await expect(page.getByText('Decision Letter')).toBeVisible()
    await expect(page.getByRole('link', { name: '返回稿件详情' })).toBeVisible()
    await expect(page.getByText('Submit Your Manuscript')).toHaveCount(0)
  })
})
