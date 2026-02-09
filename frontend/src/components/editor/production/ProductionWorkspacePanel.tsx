'use client'

import { useEffect, useMemo, useState } from 'react'
import { Loader2, Upload } from 'lucide-react'
import { toast } from 'sonner'
import { EditorApi } from '@/services/editorApi'
import type { ProductionCycle, ProductionWorkspaceContext } from '@/types/production'

type StaffOption = {
  id: string
  name: string
  email?: string | null
}

type Props = {
  manuscriptId: string
  context: ProductionWorkspaceContext
  staff: StaffOption[]
  onReload: () => Promise<void>
}

function toDateTimeLocal(raw: string | null | undefined): string {
  if (!raw) return ''
  try {
    const d = new Date(raw)
    d.setMinutes(d.getMinutes() - d.getTimezoneOffset())
    return d.toISOString().slice(0, 16)
  } catch {
    return ''
  }
}

function formatDate(raw: string | null | undefined): string {
  if (!raw) return '--'
  const d = new Date(raw)
  if (Number.isNaN(d.getTime())) return '--'
  return d.toLocaleString()
}

export function ProductionWorkspacePanel({ manuscriptId, context, staff, onReload }: Props) {
  const activeCycle = context.active_cycle || null

  const [layoutEditorId, setLayoutEditorId] = useState(staff[0]?.id || '')
  const [proofDueAt, setProofDueAt] = useState(() => {
    const n = new Date(Date.now() + 3 * 24 * 3600 * 1000)
    n.setMinutes(n.getMinutes() - n.getTimezoneOffset())
    return n.toISOString().slice(0, 16)
  })
  const [createLoading, setCreateLoading] = useState(false)

  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [versionNote, setVersionNote] = useState('')
  const [uploadDueAt, setUploadDueAt] = useState(() => toDateTimeLocal(activeCycle?.proof_due_at || proofDueAt))
  const [uploadLoading, setUploadLoading] = useState(false)

  const assignedAuthorId = useMemo(() => String(context.manuscript.author_id || ''), [context.manuscript.author_id])

  useEffect(() => {
    if (!layoutEditorId && staff[0]?.id) {
      setLayoutEditorId(staff[0].id)
    }
  }, [layoutEditorId, staff])

  const handleCreateCycle = async () => {
    if (!layoutEditorId) {
      toast.error('请选择排版负责人')
      return
    }
    if (!assignedAuthorId) {
      toast.error('缺少责任作者，无法创建轮次')
      return
    }
    if (!proofDueAt) {
      toast.error('请选择校对截止时间')
      return
    }

    setCreateLoading(true)
    try {
      const res = await EditorApi.createProductionCycle(manuscriptId, {
        layout_editor_id: layoutEditorId,
        proofreader_author_id: assignedAuthorId,
        proof_due_at: new Date(proofDueAt).toISOString(),
      })
      if (!res?.success) {
        throw new Error(res?.detail || res?.message || '创建生产轮次失败')
      }
      toast.success('生产轮次已创建')
      await onReload()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '创建生产轮次失败')
    } finally {
      setCreateLoading(false)
    }
  }

  const handleOpenGalley = async (cycle: ProductionCycle) => {
    const localUrl = cycle.galley_signed_url
    if (localUrl) {
      window.open(localUrl, '_blank', 'noopener,noreferrer')
      return
    }
    try {
      const res = await EditorApi.getProductionGalleySignedUrl(manuscriptId, cycle.id)
      if (!res?.success || !res?.data?.signed_url) {
        throw new Error(res?.detail || res?.message || '打开清样失败')
      }
      window.open(String(res.data.signed_url), '_blank', 'noopener,noreferrer')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '打开清样失败')
    }
  }

  const handleUploadGalley = async () => {
    if (!activeCycle) return
    if (!uploadFile) {
      toast.error('请选择 PDF 清样文件')
      return
    }
    if (!versionNote.trim()) {
      toast.error('请填写版本说明')
      return
    }

    setUploadLoading(true)
    try {
      const res = await EditorApi.uploadProductionGalley(manuscriptId, activeCycle.id, {
        file: uploadFile,
        version_note: versionNote,
        proof_due_at: uploadDueAt ? new Date(uploadDueAt).toISOString() : undefined,
      })
      if (!res?.success) {
        throw new Error(res?.detail || res?.message || '上传清样失败')
      }
      setUploadFile(null)
      setVersionNote('')
      toast.success('清样已上传，已通知作者校对')
      await onReload()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '上传清样失败')
    } finally {
      setUploadLoading(false)
    }
  }

  return (
    <section className="space-y-3">
      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="text-sm font-bold uppercase tracking-wide text-slate-700">Production Workspace</h2>
        <p className="mt-1 text-xs text-slate-500">创建轮次、上传清样并跟踪作者校对状态。</p>
      </div>

      {!activeCycle ? (
        <div className="rounded-lg border border-slate-200 bg-white p-4 space-y-3">
          <h3 className="text-sm font-semibold text-slate-900">Create Production Cycle</h3>
          <div>
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">Layout Editor</label>
            <select
              value={layoutEditorId}
              onChange={(event) => setLayoutEditorId(event.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="">Select editor</option>
              {staff.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name || item.email || item.id}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">Proof Due At</label>
            <input
              type="datetime-local"
              value={proofDueAt}
              onChange={(event) => setProofDueAt(event.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
          </div>

          <button
            type="button"
            onClick={() => void handleCreateCycle()}
            disabled={createLoading || !context.permissions?.can_create_cycle}
            className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-slate-900 px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"
          >
            {createLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            Create Cycle
          </button>
          {!context.permissions?.can_create_cycle ? (
            <p className="text-xs text-amber-700">当前状态或活跃轮次限制，暂不可创建新轮次。</p>
          ) : null}
        </div>
      ) : (
        <div className="rounded-lg border border-slate-200 bg-white p-4 space-y-3">
          <h3 className="text-sm font-semibold text-slate-900">Active Cycle #{activeCycle.cycle_no}</h3>
          <div className="grid grid-cols-2 gap-2 text-xs text-slate-600">
            <p>Status: <span className="font-semibold">{activeCycle.status}</span></p>
            <p>Due: <span className="font-semibold">{formatDate(activeCycle.proof_due_at)}</span></p>
          </div>

          <button
            type="button"
            onClick={() => void handleOpenGalley(activeCycle)}
            disabled={!activeCycle.galley_path}
            className="inline-flex w-full items-center justify-center rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 disabled:opacity-60"
          >
            Open Current Galley
          </button>

          <div className="space-y-2 rounded-md border border-slate-200 bg-slate-50 p-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">Upload / Replace Galley</p>
            <input
              type="file"
              accept="application/pdf,.pdf"
              onChange={(event) => setUploadFile(event.target.files?.[0] ?? null)}
              className="block w-full text-xs text-slate-600"
            />
            <textarea
              value={versionNote}
              onChange={(event) => setVersionNote(event.target.value)}
              rows={3}
              placeholder="版本说明（例如：修复图表排版 + 统一参考文献样式）"
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
            <input
              type="datetime-local"
              value={uploadDueAt}
              onChange={(event) => setUploadDueAt(event.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
            <button
              type="button"
              onClick={() => void handleUploadGalley()}
              disabled={uploadLoading || !context.permissions?.can_upload_galley}
              className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-slate-900 px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"
            >
              {uploadLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
              Upload Galley
            </button>
          </div>
        </div>
      )}
    </section>
  )
}
