import { test, expect } from '@playwright/test'
import path from 'path'
import { buildSession, fulfillJson, seedSession } from '../utils'

type Roles = Array<'author' | 'editor' | 'reviewer' | 'admin'>

async function enableE2EAuthBypass(page: import('@playwright/test').Page) {
  await page.context().setExtraHTTPHeaders({ 'x-scholarflow-e2e': '1' })
}

function buildProcessRows(args: { rows?: any[] }) {
  return args.rows ?? []
}

async function mockApi(
  page: import('@playwright/test').Page,
  opts: {
    roles: Roles
    manuscriptId: string
    initialRows?: any[]
    getProcessRows?: () => any[]
    submissions?: any[]
    manuscriptStatus?: string
    revisionRequest?: { decision_type: 'major' | 'minor'; editor_comment: string }
    getEditorDetail?: () => any
    onPatchManuscriptStatus?: (status: string) => void
    onEditorRequestRevision?: () => void
    onAuthorSubmitRevision?: () => void
  }
) {
  const nowIso = new Date().toISOString()

  await page.route('**/api/v1/**', async (route) => {
    const req = route.request()
    const url = new URL(req.url())
    const pathname = url.pathname

    if (pathname === '/api/v1/user/profile') {
      return fulfillJson(route, 200, { success: true, data: { roles: opts.roles } })
    }

    if (pathname === '/api/v1/stats/author') {
      return fulfillJson(route, 200, {
        success: true,
        data: { total_submissions: 1, published: 0, under_review: 0, revision_required: 0 },
      })
    }

    if (pathname === '/api/v1/manuscripts/mine') {
      return fulfillJson(route, 200, { success: true, data: opts.submissions ?? [] })
    }

    if (pathname === '/api/v1/editor/journals') {
      return fulfillJson(route, 200, { success: true, data: [] })
    }

    if (pathname === '/api/v1/editor/internal-staff') {
      return fulfillJson(route, 200, { success: true, data: [] })
    }

    if (pathname === '/api/v1/editor/rbac/context') {
      return fulfillJson(route, 200, {
        success: true,
        data: {
          roles: opts.roles,
          normalized_roles: opts.roles,
          allowed_actions: [
            'process:view',
            'manuscript:view_detail',
            'decision:record_first',
            'decision:submit_final',
            'manuscript:bind_owner',
          ],
          journal_scope: {
            enforcement_enabled: false,
            is_admin: true,
            allowed_journal_ids: [],
          },
        },
      })
    }

    if (pathname === '/api/v1/editor/manuscripts/process') {
      const data = opts.getProcessRows ? opts.getProcessRows() : buildProcessRows({ rows: opts.initialRows })
      return fulfillJson(route, 200, { success: true, data })
    }

    if (pathname === `/api/v1/editor/manuscripts/${opts.manuscriptId}` && req.method() === 'GET') {
      const detail =
        opts.getEditorDetail?.() || {
          id: opts.manuscriptId,
          title: 'Mocked manuscript',
          status: opts.manuscriptStatus ?? 'minor_revision',
          updated_at: nowIso,
          owner: { id: 'o1', full_name: 'Owner A', email: 'owner@example.com' },
          editor: { id: 'e1', full_name: 'Editor A', email: 'editor@example.com' },
          invoice: { status: 'unpaid', amount: 1000 },
          files: [],
          signed_files: {
            original_manuscript: { path: `${opts.manuscriptId}/v1_initial.pdf`, signed_url: '/favicon.svg' },
            peer_review_reports: [],
          },
        }
      return fulfillJson(route, 200, { success: true, data: detail })
    }

    if (pathname === `/api/v1/editor/manuscripts/${opts.manuscriptId}/status` && req.method() === 'PATCH') {
      let status = ''
      try {
        const body = (await req.postDataJSON()) as any
        status = String(body?.status || '')
      } catch {
        status = ''
      }
      if (status) opts.onPatchManuscriptStatus?.(status)
      return fulfillJson(route, 200, {
        success: true,
        data: { id: opts.manuscriptId, status, updated_at: new Date().toISOString() },
      })
    }

    if (pathname === '/api/v1/editor/revisions' && req.method() === 'POST') {
      opts.onEditorRequestRevision?.()
      return fulfillJson(route, 200, {
        success: true,
        data: {
          id: '00000000-0000-0000-0000-000000000001',
          manuscript_id: opts.manuscriptId,
          round_number: 1,
          decision_type: 'minor',
          editor_comment: 'Mocked revision request.',
          status: 'pending',
          created_at: nowIso,
          submitted_at: null,
          response_letter: null,
        },
      })
    }

    if (pathname === `/api/v1/manuscripts/by-id/${opts.manuscriptId}`) {
      return fulfillJson(route, 200, {
        success: true,
        data: {
          id: opts.manuscriptId,
          title: 'Mocked manuscript',
          abstract: 'Mocked abstract',
          status: opts.manuscriptStatus ?? 'minor_revision',
          version: 1,
          updated_at: nowIso,
        },
      })
    }

    if (pathname === `/api/v1/manuscripts/${opts.manuscriptId}/versions`) {
      return fulfillJson(route, 200, {
        success: true,
        data: {
          versions: [{ id: 'v1', version_number: 1, file_path: `${opts.manuscriptId}/v1_initial.pdf` }],
          revisions: [
            {
              id: 'r1',
              manuscript_id: opts.manuscriptId,
              round_number: 1,
              decision_type: opts.revisionRequest?.decision_type ?? 'minor',
              editor_comment: opts.revisionRequest?.editor_comment ?? 'Please update references and fix typos.',
              status: 'pending',
              created_at: nowIso,
              submitted_at: null,
              response_letter: null,
            },
          ],
        },
      })
    }

    if (pathname === `/api/v1/manuscripts/${opts.manuscriptId}/revisions` && req.method() === 'POST') {
      opts.onAuthorSubmitRevision?.()
      return fulfillJson(route, 200, {
        success: true,
        data: { new_version: { version_number: 2 }, revision_id: 'r1', manuscript_status: 'resubmitted' },
      })
    }

    // 默认兜底：避免未覆盖的 API 请求导致测试挂起
    return fulfillJson(route, 200, { success: true, data: {} })
  })
}

test.describe('Revision workflow (mocked backend)', () => {
  test('Editor requests revision flow', async ({ page }) => {
    const manuscriptId = '11111111-1111-1111-1111-111111111111'
    await enableE2EAuthBypass(page)
    await seedSession(page, buildSession('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'editor@example.com'))

    let manuscriptStatus = 'pre_check'
    await mockApi(page, {
      roles: ['managing_editor'],
      manuscriptId,
      getEditorDetail: () => ({
        id: manuscriptId,
        title: 'Mocked manuscript',
        abstract: 'Mocked abstract',
        status: manuscriptStatus,
        version: 1,
        updated_at: new Date().toISOString(),
        owner: { id: 'o1', full_name: 'Owner A', email: 'owner@example.com' },
        editor: { id: 'e1', full_name: 'Editor A', email: 'editor@example.com' },
        invoice: { status: 'unpaid', amount: 1000 },
        files: [],
        signed_files: {
          original_manuscript: { path: `${manuscriptId}/v1_initial.pdf`, signed_url: '/favicon.svg' },
          peer_review_reports: [],
        },
      }),
      onPatchManuscriptStatus: (status) => {
        manuscriptStatus = status
      },
    })

    await page.goto(`/editor/manuscript/${manuscriptId}`)
    await expect(page.getByRole('heading', { name: 'Mocked manuscript' })).toBeVisible()

    await page.getByRole('button', { name: /Request Technical Return|Move to Minor Revision/i }).click()
    const dialog = page.getByRole('dialog', { name: 'Confirm Status Transition' })
    await expect(dialog).toBeVisible()
    await dialog.getByRole('textbox').fill('Please fix the formatting and update references.')
    await dialog.getByRole('button', { name: 'Confirm' }).click()

    await expect(page.getByText('Minor Revision')).toBeVisible()
  })

  test('Author submits revision flow (button visibility + submit)', async ({ page }) => {
    const manuscriptId = '22222222-2222-2222-2222-222222222222'

    await enableE2EAuthBypass(page)
    await seedSession(page, buildSession('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'author@example.com'))

    await mockApi(page, {
      roles: ['author'],
      manuscriptId,
      submissions: [{ id: manuscriptId, title: 'E2E Manuscript', status: 'minor_revision', created_at: new Date().toISOString() }],
      revisionRequest: { decision_type: 'minor', editor_comment: 'Please update references and fix typos.' },
    })

    await page.goto(`/submit-revision/${manuscriptId}`)

    await expect(page.getByRole('heading', { name: 'Submit Revision' })).toBeVisible()
    await expect(page.getByText("Editor's Request")).toBeVisible()
    await expect(page.getByText('Please update references and fix typos.')).toBeVisible()

    const pdfPath = path.join(__dirname, '..', 'fixtures', 'revised.pdf')
    await page.locator('#file-upload').setInputFiles(pdfPath)

    const editor = page.locator('.ProseMirror')
    await editor.click()
    await editor.fill('I have updated the references and fixed all typos as requested. Thanks!')

    await page.getByRole('button', { name: 'Submit Revision' }).click()
    await page.waitForURL('**/dashboard')
  })

  test('Editor verifies resubmission visibility (Resubmitted column)', async ({ page }) => {
    const manuscriptId = '33333333-3333-3333-3333-333333333333'

    await enableE2EAuthBypass(page)
    await seedSession(page, buildSession('cccccccc-cccc-cccc-cccc-cccccccccccc', 'editor@example.com'))

    await mockApi(page, {
      roles: ['managing_editor'],
      manuscriptId,
      initialRows: [{ id: manuscriptId, status: 'resubmitted', created_at: new Date().toISOString(), updated_at: new Date().toISOString() }],
    })

    await page.goto('/editor/process')

    await expect(page.getByTestId('editor-process-table')).toBeVisible()
    const table = page.getByTestId('editor-process-table')
    await expect(table.getByText(manuscriptId)).toBeVisible()
    await expect(table.getByText('Resubmitted')).toBeVisible()
  })
})
