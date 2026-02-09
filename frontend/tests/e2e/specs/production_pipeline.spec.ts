import { expect, test } from '@playwright/test'
import { buildSession, fulfillJson, seedSession } from '../utils'

test.describe('Production pipeline workspace flow (mocked)', () => {
  test('editor can create cycle, upload galley and approve for publication', async ({ page }) => {
    const manuscriptId = '00000000-0000-0000-0000-000000004201'
    await page.context().setExtraHTTPHeaders({ 'x-scholarflow-e2e': '1' })
    await seedSession(page, buildSession('11111111-1111-1111-1111-111111111111', 'editor@example.com'))

    let hasCycle = false
    let cycleStatus: string = 'draft'
    let created = 0
    let uploaded = 0
    let approved = 0

    await page.route('**/api/v1/**', async (route) => {
      const req = route.request()
      const pathname = new URL(req.url()).pathname

      if (pathname === `/api/v1/editor/manuscripts/${manuscriptId}/production-workspace`) {
        return fulfillJson(route, 200, {
          success: true,
          data: {
            manuscript: {
              id: manuscriptId,
              title: 'Production Workspace Mock Manuscript',
              status: 'approved',
              author_id: '22222222-2222-2222-2222-222222222222',
              pdf_url: 'https://example.com/mock-manuscript.pdf',
            },
            active_cycle: hasCycle
              ? {
                  id: 'cycle-1',
                  manuscript_id: manuscriptId,
                  cycle_no: 1,
                  status: cycleStatus,
                  layout_editor_id: '11111111-1111-1111-1111-111111111111',
                  proofreader_author_id: '22222222-2222-2222-2222-222222222222',
                  galley_bucket: 'production-proofs',
                  galley_path: 'production_cycles/mock/cycle-1/proof.pdf',
                  galley_signed_url: 'https://example.com/galley.pdf',
                  proof_due_at: new Date(Date.now() + 2 * 24 * 3600 * 1000).toISOString(),
                  latest_response:
                    cycleStatus === 'author_confirmed'
                      ? {
                          decision: 'confirm_clean',
                          submitted_at: new Date().toISOString(),
                          summary: 'Looks good',
                          corrections: [],
                        }
                      : null,
                }
              : null,
            cycle_history: hasCycle
              ? [
                  {
                    id: 'cycle-1',
                    manuscript_id: manuscriptId,
                    cycle_no: 1,
                    status: cycleStatus,
                    layout_editor_id: '11111111-1111-1111-1111-111111111111',
                    proofreader_author_id: '22222222-2222-2222-2222-222222222222',
                    proof_due_at: new Date(Date.now() + 2 * 24 * 3600 * 1000).toISOString(),
                  },
                ]
              : [],
            permissions: {
              can_create_cycle: !hasCycle,
              can_upload_galley: hasCycle,
              can_approve: hasCycle && cycleStatus === 'author_confirmed',
            },
          },
        })
      }

      if (pathname === '/api/v1/editor/internal-staff') {
        return fulfillJson(route, 200, {
          success: true,
          data: [{ id: '11111111-1111-1111-1111-111111111111', full_name: 'Editor One', email: 'editor@example.com' }],
        })
      }

      if (pathname === `/api/v1/editor/manuscripts/${manuscriptId}/production-cycles` && req.method() === 'POST') {
        hasCycle = true
        cycleStatus = 'draft'
        created += 1
        return fulfillJson(route, 201, {
          success: true,
          data: {
            cycle: {
              id: 'cycle-1',
              manuscript_id: manuscriptId,
              cycle_no: 1,
              status: 'draft',
              layout_editor_id: '11111111-1111-1111-1111-111111111111',
              proofreader_author_id: '22222222-2222-2222-2222-222222222222',
            },
          },
        })
      }

      if (
        pathname === `/api/v1/editor/manuscripts/${manuscriptId}/production-cycles/cycle-1/galley` &&
        req.method() === 'POST'
      ) {
        uploaded += 1
        cycleStatus = 'author_confirmed'
        return fulfillJson(route, 200, {
          success: true,
          data: {
            cycle: {
              id: 'cycle-1',
              manuscript_id: manuscriptId,
              cycle_no: 1,
              status: 'author_confirmed',
              galley_path: 'production_cycles/mock/cycle-1/proof.pdf',
              galley_signed_url: 'https://example.com/galley.pdf',
            },
          },
        })
      }

      if (
        pathname === `/api/v1/editor/manuscripts/${manuscriptId}/production-cycles/cycle-1/approve` &&
        req.method() === 'POST'
      ) {
        approved += 1
        cycleStatus = 'approved_for_publish'
        return fulfillJson(route, 200, {
          success: true,
          data: {
            cycle_id: 'cycle-1',
            status: 'approved_for_publish',
            approved_at: new Date().toISOString(),
            approved_by: '11111111-1111-1111-1111-111111111111',
          },
        })
      }

      return route.fulfill({ status: 404, body: 'not mocked' })
    })

    await page.goto(`/editor/production/${manuscriptId}`)

    await expect(page.getByText('Production Pipeline Workspace')).toBeVisible()
    await expect(page.getByText('Create Production Cycle')).toBeVisible()

    await page.getByRole('button', { name: 'Create Cycle' }).click()
    await expect.poll(() => created).toBe(1)

    await page.setInputFiles('input[type="file"]', {
      name: 'proof.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('%PDF-1.4\n%mock file'),
    })
    await page.getByPlaceholder('版本说明（例如：修复图表排版 + 统一参考文献样式）').fill('v1 galley')
    await page.getByRole('button', { name: 'Upload Galley' }).click()

    await expect.poll(() => uploaded).toBe(1)

    await page.getByRole('button', { name: 'Approve for Publication' }).click()
    await expect.poll(() => approved).toBe(1)
  })

  test('author can submit correction list in proofreading page', async ({ page }) => {
    const manuscriptId = '00000000-0000-0000-0000-000000004202'
    await page.context().setExtraHTTPHeaders({ 'x-scholarflow-e2e': '1' })
    await seedSession(page, buildSession('22222222-2222-2222-2222-222222222222', 'author@example.com'))

    const payloads: any[] = []

    await page.route('**/api/v1/**', async (route) => {
      const req = route.request()
      const pathname = new URL(req.url()).pathname

      if (pathname === `/api/v1/manuscripts/${manuscriptId}/proofreading-context`) {
        return fulfillJson(route, 200, {
          success: true,
          data: {
            manuscript: {
              id: manuscriptId,
              title: 'Author Proofreading Mock Manuscript',
              status: 'proofreading',
            },
            cycle: {
              id: 'cycle-2',
              manuscript_id: manuscriptId,
              cycle_no: 2,
              status: 'awaiting_author',
              layout_editor_id: '11111111-1111-1111-1111-111111111111',
              proofreader_author_id: '22222222-2222-2222-2222-222222222222',
              galley_signed_url: 'https://example.com/galley.pdf',
              proof_due_at: new Date(Date.now() + 2 * 24 * 3600 * 1000).toISOString(),
            },
            can_submit: true,
            is_read_only: false,
          },
        })
      }

      if (
        pathname === `/api/v1/manuscripts/${manuscriptId}/production-cycles/cycle-2/proofreading` &&
        req.method() === 'POST'
      ) {
        payloads.push(req.postDataJSON())
        return fulfillJson(route, 200, {
          success: true,
          data: {
            response_id: 'resp-1',
            cycle_id: 'cycle-2',
            decision: 'submit_corrections',
            submitted_at: new Date().toISOString(),
          },
        })
      }

      if (pathname === `/api/v1/manuscripts/${manuscriptId}/production-cycles/cycle-2/galley-signed`) {
        return fulfillJson(route, 200, {
          success: true,
          data: { signed_url: 'https://example.com/galley.pdf' },
        })
      }

      return route.fulfill({ status: 404, body: 'not mocked' })
    })

    await page.goto(`/proofreading/${manuscriptId}`)

    await expect(page.getByRole('heading', { name: 'Author Proofreading Mock Manuscript' })).toBeVisible()
    await page.getByLabel('Submit correction list').check()
    await page.getByPlaceholder('例如：整体可发布，仅需修正图2注释。').fill('Need minor wording adjustments')
    await page.getByPlaceholder('Suggested correction (required)').first().fill('Replace typo in abstract')

    await page.getByRole('button', { name: 'Submit Proofreading' }).click()

    await expect.poll(() => payloads.length).toBe(1)
    expect(payloads[0].decision).toBe('submit_corrections')
    expect(payloads[0].corrections.length).toBe(1)
    expect(payloads[0].corrections[0].suggested_text).toContain('Replace typo')
  })
})
