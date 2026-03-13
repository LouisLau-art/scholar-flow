import { expect, test } from '@playwright/test'

import { AuthorManuscriptPage } from '../pages/author-manuscript.page'
import { buildSession, fulfillJson, seedSession } from '../utils'

test.describe('Author manuscript context (mocked)', () => {
  test('renders submission email and corresponding author emails from author-context', async ({ page }) => {
    const manuscriptId = '33333333-3333-4333-8333-333333333333'
    await page.context().setExtraHTTPHeaders({ 'x-scholarflow-e2e': '1' })
    await seedSession(page, buildSession('44444444-4444-4444-8444-444444444444', 'author@example.com'))

    await page.route('**/api/v1/**', async (route) => {
      const req = route.request()
      const url = new URL(req.url())
      const path = url.pathname

      if (path === '/api/v1/user/profile') {
        return fulfillJson(route, 200, {
          success: true,
          data: {
            id: '44444444-4444-4444-8444-444444444444',
            email: 'author@example.com',
            full_name: 'Author Example',
            roles: ['author'],
          },
        })
      }

      if (path === '/api/v1/cms/menu') {
        return fulfillJson(route, 200, {
          success: true,
          data: [],
        })
      }

      if (path === `/api/v1/manuscripts/${manuscriptId}/author-context`) {
        return fulfillJson(route, 200, {
          success: true,
          data: {
            manuscript: {
              id: manuscriptId,
              title: 'Author Context Smoke Manuscript',
              status: 'major_revision',
              status_label: 'Major Revision',
              created_at: '2026-03-13T12:00:00Z',
              updated_at: '2026-03-13T12:30:00Z',
              submission_email: 'delegate@example.com',
              author_contacts: [
                {
                  name: 'Lead Author',
                  email: 'lead.author@example.com',
                  is_corresponding: true,
                },
                {
                  name: 'Second Author',
                  email: 'second.author@example.com',
                  is_corresponding: false,
                },
              ],
            },
            files: {
              current_pdf_signed_url: null,
              word_manuscripts: [],
            },
            proofreading_task: null,
            timeline: [],
          },
        })
      }

      return fulfillJson(route, 200, { success: true, data: {} })
    })

    const authorPage = new AuthorManuscriptPage(page)
    await authorPage.goto(manuscriptId)

    await expect(authorPage.title('Author Context Smoke Manuscript')).toBeVisible()
    await expect(authorPage.statusHeading()).toBeVisible()
    await expect(authorPage.fieldLabel('Submission Email')).toBeVisible()
    await expect(authorPage.fieldValue('delegate@example.com')).toBeVisible()
    await expect(authorPage.fieldLabel('Corresponding Author Email(s)')).toBeVisible()
    await expect(authorPage.fieldValue('lead.author@example.com')).toBeVisible()
  })
})
