import { test, expect } from '@playwright/test'
import path from 'path'
import { buildSession, fulfillJson, seedSession } from '../utils'

type Roles = Array<'author' | 'editor' | 'reviewer' | 'admin'>

async function enableE2EAuthBypass(page: import('@playwright/test').Page) {
  await page.context().setExtraHTTPHeaders({ 'x-scholarflow-e2e': '1' })
}

function buildPipeline({
  pendingDecision = [],
  revisionRequested = [],
  resubmitted = [],
}: {
  pendingDecision?: any[]
  revisionRequested?: any[]
  resubmitted?: any[]
}) {
  return {
    pending_quality: [],
    under_review: [],
    pending_decision: pendingDecision,
    published: [],
    revision_requested: revisionRequested,
    resubmitted,
  }
}

async function mockApi(
  page: import('@playwright/test').Page,
  opts: {
    roles: Roles
    manuscriptId: string
    manuscriptTitle: string
    initialPipeline?: any
    getEditorPipeline?: () => any
    submissions?: any[]
    manuscriptStatus?: string
    revisionRequest?: { decision_type: 'major' | 'minor'; editor_comment: string }
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

    if (pathname === '/api/v1/editor/pipeline') {
      const data = opts.getEditorPipeline ? opts.getEditorPipeline() : (opts.initialPipeline ?? buildPipeline({}))
      return fulfillJson(route, 200, { success: true, data })
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

    if (pathname === `/api/v1/manuscripts/articles/${opts.manuscriptId}`) {
      return fulfillJson(route, 200, {
        success: true,
        data: {
          id: opts.manuscriptId,
          title: opts.manuscriptTitle,
          abstract: 'Mocked abstract',
          status: opts.manuscriptStatus ?? 'revision_requested',
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
    const manuscriptTitle = 'E2E Manuscript - Pending Decision'

    await enableE2EAuthBypass(page)
    await seedSession(page, buildSession('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'editor@example.com'))

    let revisionRequested = false
    await mockApi(page, {
      roles: ['editor'],
      manuscriptId,
      manuscriptTitle,
      getEditorPipeline: () =>
        revisionRequested
          ? buildPipeline({
              revisionRequested: [{ id: manuscriptId, title: manuscriptTitle, updated_at: new Date().toISOString() }],
            })
          : buildPipeline({ pendingDecision: [{ id: manuscriptId, title: manuscriptTitle }] }),
      onEditorRequestRevision: () => {
        revisionRequested = true
      },
    })

    await page.goto('/dashboard')
    await expect(page.getByText('roles:')).toBeVisible({ timeout: 15000 })
    await page.getByRole('tab', { name: /Editor/i }).click()

    await expect(page.getByTestId('editor-pipeline')).toBeVisible()
    await expect(page.getByText(manuscriptTitle)).toBeVisible()

    // 打开决策面板
    await page.getByRole('button', { name: 'Make Decision' }).click()
    await expect(page.getByRole('heading', { name: 'Final Decision' })).toBeVisible()

    // 选择 Request Revision -> Minor -> 填写说明 -> 提交
    await page.getByText('Request Revision').click()
    await page.getByRole('radio', { name: 'Minor Revision', exact: true }).click()
    await page.locator('textarea').fill('Please fix the formatting and update references.')
    await page.getByRole('button', { name: 'Submit Decision' }).click()

    // 回到 pipeline 后应出现 Waiting for Author（revision_requested）
    await expect(page.getByTestId('editor-pipeline')).toBeVisible()
    await expect(
      page.getByTestId('editor-pipeline-list').getByRole('heading', { name: 'Waiting for Author' })
    ).toBeVisible()
    await expect(page.getByText(manuscriptTitle)).toBeVisible()
  })

  test('Author submits revision flow (button visibility + submit)', async ({ page }) => {
    const manuscriptId = '22222222-2222-2222-2222-222222222222'
    const manuscriptTitle = 'E2E Manuscript - Revision Requested'

    await enableE2EAuthBypass(page)
    await seedSession(page, buildSession('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'author@example.com'))

    await mockApi(page, {
      roles: ['author'],
      manuscriptId,
      manuscriptTitle,
      submissions: [{ id: manuscriptId, title: manuscriptTitle, status: 'revision_requested', created_at: new Date().toISOString() }],
      revisionRequest: { decision_type: 'minor', editor_comment: 'Please update references and fix typos.' },
    })

    await page.goto('/dashboard')
    await expect(page.getByRole('link', { name: 'Submit Revision' })).toBeVisible()
    await page.getByRole('link', { name: 'Submit Revision' }).click()

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
    const manuscriptTitle = 'E2E Manuscript - Resubmitted'

    await enableE2EAuthBypass(page)
    await seedSession(page, buildSession('cccccccc-cccc-cccc-cccc-cccccccccccc', 'editor@example.com'))

    await mockApi(page, {
      roles: ['editor'],
      manuscriptId,
      manuscriptTitle,
      initialPipeline: buildPipeline({
        resubmitted: [{ id: manuscriptId, title: manuscriptTitle, updated_at: new Date().toISOString(), version: 2 }],
      }),
    })

    await page.goto('/dashboard')
    await page.getByRole('tab', { name: /Editor/i }).click()

    await expect(page.getByTestId('editor-pipeline')).toBeVisible()
    await expect(page.getByText('Resubmitted Revisions')).toBeVisible()
    await expect(page.getByText(manuscriptTitle)).toBeVisible()
  })
})
