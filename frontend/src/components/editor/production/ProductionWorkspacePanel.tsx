'use client'

import { useEffect, useMemo, useState } from 'react'
import { Loader2, Upload, X } from 'lucide-react'
import { toast } from 'sonner'
import { EditorApi } from '@/services/editorApi'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { DateTimePicker } from '@/components/ui/date-time-picker'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import type { ProductionCycle, ProductionWorkspaceContext } from '@/types/production'

type StaffOption = {
  id: string
  name: string
  email?: string | null
  roles?: string[] | null
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

  const productionStaff = useMemo(() => {
    return staff.filter((row) => {
      const roles = (row.roles || []).map((r) => String(r || '').toLowerCase())
      return roles.includes('production_editor') || roles.includes('admin')
    })
  }, [staff])

  const staffNameById = useMemo(() => {
    const map = new Map<string, string>()
    staff.forEach((row) => {
      map.set(String(row.id), String(row.name || row.email || row.id))
    })
    return map
  }, [staff])

  const [layoutEditorId, setLayoutEditorId] = useState(productionStaff[0]?.id || '')
  const [collaboratorIds, setCollaboratorIds] = useState<string[]>([])
  const [collaboratorPick, setCollaboratorPick] = useState<string>('')
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
    if (!layoutEditorId && productionStaff[0]?.id) {
      setLayoutEditorId(productionStaff[0].id)
    }
  }, [layoutEditorId, productionStaff])

  useEffect(() => {
    if (!activeCycle) return
    // active cycle -> sync UI state (ME/EIC/Admin may adjust editors)
    setLayoutEditorId(String(activeCycle.layout_editor_id || ''))
    setCollaboratorIds((activeCycle.collaborator_editor_ids || []).map((v) => String(v)))
    setCollaboratorPick('')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeCycle?.id])

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
        collaborator_editor_ids: collaboratorIds,
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

  const handleUpdateEditors = async () => {
    if (!activeCycle) return
    if (!layoutEditorId) {
      toast.error('请选择排版负责人')
      return
    }
    setCreateLoading(true)
    try {
      const res = await EditorApi.updateProductionCycleEditors(manuscriptId, activeCycle.id, {
        layout_editor_id: layoutEditorId,
        collaborator_editor_ids: collaboratorIds,
      })
      if (!res?.success) {
        throw new Error(res?.detail || res?.message || '更新负责人失败')
      }
      toast.success('负责人已更新')
      await onReload()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '更新负责人失败')
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
      <div className="rounded-lg border border-border bg-card p-4">
        <h2 className="text-sm font-bold uppercase tracking-wide text-muted-foreground">Production Workspace</h2>
        <p className="mt-1 text-xs text-muted-foreground">创建轮次、上传清样并跟踪作者校对状态。</p>
      </div>

      {!activeCycle ? (
        <div className="rounded-lg border border-border bg-card p-4 space-y-3">
          <h3 className="text-sm font-semibold text-foreground">Create Production Cycle</h3>
          <div>
            <Label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Layout Editor</Label>
            <Select value={layoutEditorId} onValueChange={setLayoutEditorId}>
              <SelectTrigger>
                <SelectValue placeholder="Select editor" />
              </SelectTrigger>
              <SelectContent>
                {productionStaff.map((item) => (
                  <SelectItem key={item.id} value={item.id}>
                    {item.name || item.email || item.id}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {productionStaff.length === 0 ? (
              <p className="mt-1 text-xs text-destructive">未找到 production_editor 账号，请先在 Admin User Management 里分配 Production Editor 角色。</p>
            ) : null}
          </div>

          <div>
            <Label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Collaborators (Optional)</Label>
            {collaboratorIds.length ? (
              <div className="flex flex-wrap gap-2 pb-2">
                {collaboratorIds.map((cid) => (
                  <Badge key={cid} variant="secondary" className="gap-1">
                    {staffNameById.get(cid) || cid}
                    <button
                      type="button"
                      className="ml-1 inline-flex items-center text-muted-foreground hover:text-foreground"
                      onClick={() => setCollaboratorIds((prev) => prev.filter((x) => x !== cid))}
                      aria-label="Remove collaborator"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                ))}
              </div>
            ) : null}
            <Select
              value={collaboratorPick}
              onValueChange={(value) => {
                const v = String(value || '').trim()
                if (!v) return
                if (v === layoutEditorId) {
                  toast.error('协作者不能与主负责人重复')
                  setCollaboratorPick('')
                  return
                }
                setCollaboratorIds((prev) => (prev.includes(v) ? prev : [...prev, v]))
                setCollaboratorPick('')
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="Add collaborator…" />
              </SelectTrigger>
              <SelectContent>
                {productionStaff
                  .filter((item) => item.id !== layoutEditorId && !collaboratorIds.includes(item.id))
                  .map((item) => (
                    <SelectItem key={item.id} value={item.id}>
                      {item.name || item.email || item.id}
                    </SelectItem>
                  ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Proof Due At</Label>
            <DateTimePicker value={proofDueAt} onChange={setProofDueAt} />
          </div>

          <Button
            type="button"
            onClick={() => void handleCreateCycle()}
            disabled={createLoading || !context.permissions?.can_create_cycle}
            className="w-full gap-2"
          >
            {createLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            Create Cycle
          </Button>
          {!context.permissions?.can_create_cycle ? (
            <p className="text-xs text-destructive">当前状态或活跃轮次限制，暂不可创建新轮次。</p>
          ) : null}
        </div>
      ) : (
        <div className="rounded-lg border border-border bg-card p-4 space-y-3">
          <h3 className="text-sm font-semibold text-foreground">Active Cycle #{activeCycle.cycle_no}</h3>
          <div className="grid grid-cols-2 gap-2 text-xs text-muted-foreground">
            <p>Status: <span className="font-semibold">{activeCycle.status}</span></p>
            <p>Due: <span className="font-semibold">{formatDate(activeCycle.proof_due_at)}</span></p>
          </div>

          {context.permissions?.can_manage_editors ? (
            <div className="space-y-2 rounded-md border border-border bg-muted/50 p-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Editors</p>
              <Select value={layoutEditorId} onValueChange={setLayoutEditorId}>
                <SelectTrigger className="h-9">
                  <SelectValue placeholder="Select layout editor" />
                </SelectTrigger>
                <SelectContent>
                  {productionStaff.map((item) => (
                    <SelectItem key={item.id} value={item.id}>
                      {item.name || item.email || item.id}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              {collaboratorIds.length ? (
                <div className="flex flex-wrap gap-2">
                  {collaboratorIds.map((cid) => (
                    <Badge key={cid} variant="secondary" className="gap-1">
                      {staffNameById.get(cid) || cid}
                      <button
                        type="button"
                        className="ml-1 inline-flex items-center text-muted-foreground hover:text-foreground"
                        onClick={() => setCollaboratorIds((prev) => prev.filter((x) => x !== cid))}
                        aria-label="Remove collaborator"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </Badge>
                  ))}
                </div>
              ) : null}

              <Select
                value={collaboratorPick}
                onValueChange={(value) => {
                  const v = String(value || '').trim()
                  if (!v) return
                  if (v === layoutEditorId) {
                    toast.error('协作者不能与主负责人重复')
                    setCollaboratorPick('')
                    return
                  }
                  setCollaboratorIds((prev) => (prev.includes(v) ? prev : [...prev, v]))
                  setCollaboratorPick('')
                }}
              >
                <SelectTrigger className="h-9">
                  <SelectValue placeholder="Add collaborator…" />
                </SelectTrigger>
                <SelectContent>
                  {productionStaff
                    .filter((item) => item.id !== layoutEditorId && !collaboratorIds.includes(item.id))
                    .map((item) => (
                      <SelectItem key={item.id} value={item.id}>
                        {item.name || item.email || item.id}
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>

              <Button type="button" variant="outline" onClick={() => void handleUpdateEditors()} disabled={createLoading}>
                {createLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Update Editors
              </Button>
            </div>
          ) : null}

          <Button
            type="button"
            variant="outline"
            onClick={() => void handleOpenGalley(activeCycle)}
            disabled={!activeCycle.galley_path}
            className="w-full"
          >
            Open Current Galley
          </Button>

          <div className="space-y-2 rounded-md border border-border bg-muted/50 p-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Upload / Replace Galley</p>
            <Input
              type="file"
              accept="application/pdf,.pdf"
              onChange={(event) => setUploadFile(event.target.files?.[0] ?? null)}
              className="w-full text-xs text-muted-foreground file:mr-3 file:rounded-md file:border-0 file:bg-primary file:px-3 file:py-1.5 file:text-xs file:font-semibold file:text-primary-foreground hover:file:bg-primary/90"
            />
            <Textarea
              value={versionNote}
              onChange={(event) => setVersionNote(event.target.value)}
              rows={3}
              placeholder="版本说明（例如：修复图表排版 + 统一参考文献样式）"
            />
            <DateTimePicker value={uploadDueAt} onChange={setUploadDueAt} />
            <Button
              type="button"
              onClick={() => void handleUploadGalley()}
              disabled={uploadLoading || !context.permissions?.can_upload_galley}
              className="w-full gap-2"
            >
              {uploadLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
              Upload Galley
            </Button>
          </div>
        </div>
      )}
    </section>
  )
}
