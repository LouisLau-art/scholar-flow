import { test, expect } from '@playwright/test'
import { EditorPage } from '../pages/editor.page'
import { fulfillJson } from '../utils'

test.describe('Editor dashboard', () => {
  test('shows pending manuscripts list', async ({ page }) => {
    await page.route('**/api/v1/stats/author', async (route) => {
      await fulfillJson(route, 200, { success: true, data: { total_submissions: 1 } })
    })
    await page.route('**/api/v1/editor/pipeline', async (route) => {
      await fulfillJson(route, 200, {
        success: true,
        data: {
          pending_quality: [
            { id: 'ms-1', title: 'Queued Manuscript', created_at: new Date().toISOString() },
          ],
          under_review: [],
          pending_decision: [],
          published: [],
        },
      })
    })

    const editor = new EditorPage(page)
    await editor.open()

    await expect(page.getByTestId('editor-pipeline')).toBeVisible()
    await expect(page.getByText('Queued Manuscript')).toBeVisible()
  })

  test('assigns reviewer from modal', async ({ page }) => {
    await page.route('**/api/v1/stats/author', async (route) => {
      await fulfillJson(route, 200, { success: true, data: { total_submissions: 1 } })
    })
    await page.route('**/api/v1/editor/pipeline', async (route) => {
      await fulfillJson(route, 200, {
        success: true,
        data: { pending_quality: [], under_review: [], pending_decision: [], published: [] },
      })
    })
    await page.route('**/api/v1/editor/available-reviewers', async (route) => {
      await fulfillJson(route, 200, {
        success: true,
        data: [
          { id: 'rev-1', name: 'Dr. Ada', email: 'ada@example.com', affiliation: 'Test Lab', expertise: ['AI'], review_count: 4 },
        ],
      })
    })

    const editor = new EditorPage(page)
    await editor.open()
    await editor.openAssignModal()

    await expect(page.getByTestId('reviewer-modal')).toBeVisible()
    await editor.assignReviewer('rev-1')
    await expect(page.getByTestId('reviewer-modal')).toBeHidden()
  })
})
