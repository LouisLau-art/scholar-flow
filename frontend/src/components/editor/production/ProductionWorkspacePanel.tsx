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
  const [proofDueAt, setProofDueAt] = useState(() => {
    const n = new Date(Date.now() + 3 * 24 * 3600 * 1000)
    n.setMinutes(n.getMinutes() - n.getTimezoneOffset())
    return n.toISOString().slice(0, 16)
  })
  const [createLoading, setCreateLoading] = useState(false)

  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [versionNote, setVersionNote] = useState('')
  const [uploadKind, setUploadKind] = useState('typeset_output')
  const [uploadLoading, setUploadLoading] = useState(false)

  // SOP Assignments
  const [coordinatorAeId, setCoordinatorAeId] = useState('')
  const [typesetterId, setTypesetterId] = useState('')
  const [languageEditorId, setLanguageEditorId] = useState('')
  const [pdfEditorId, setPdfEditorId] = useState('')

  const assignedAuthorId = useMemo(() => String(context.manuscript.author_id || ''), [context.manuscript.author_id])

  useEffect(() => {
    if (!layoutEditorId && productionStaff[0]?.id) {
      setLayoutEditorId(productionStaff[0].id)
    }
  }, [layoutEditorId, productionStaff])

  useEffect(() => {
    if (!activeCycle) return
    setLayoutEditorId(String(activeCycle.layout_editor_id || ''))
    setCollaboratorIds((activeCycle.collaborator_editor_ids || []).map((v) => String(v)))
    
    setCoordinatorAeId(activeCycle.coordinator_ae_id || '')
    setTypesetterId(activeCycle.typesetter_id || '')
    setLanguageEditorId(activeCycle.language_editor_id || '')
    setPdfEditorId(activeCycle.pdf_editor_id || '')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeCycle?.id])

  const handleCreateCycle = async () => {
    if (!layoutEditorId) {
      toast.error('请选择负责人')
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

  const handleUpdateAssignments = async () => {
    if (!activeCycle) return
    setCreateLoading(true)
    try {
      const res = await EditorApi.updateProductionCycleAssignments(manuscriptId, activeCycle.id, {
        coordinator_ae_id: coordinatorAeId || undefined,
        typesetter_id: typesetterId || undefined,
        language_editor_id: languageEditorId || undefined,
        pdf_editor_id: pdfEditorId || undefined,
      })
      if (!res?.success) {
        throw new Error(res?.detail || res?.message || '更新 SOP 分配失败')
      }
      toast.success('SOP 负责人已更新')
      await onReload()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '更新负责人失败')
    } finally {
      setCreateLoading(false)
    }
  }

  const handleUploadArtifact = async () => {
    if (!activeCycle) return
    if (!uploadFile) {
      toast.error('请选择文件')
      return
    }

    setUploadLoading(true)
    try {
      const res = await EditorApi.uploadProductionArtifact(manuscriptId, activeCycle.id, {
        artifact_kind: uploadKind,
        file: uploadFile,
        version_note: versionNote,
      })
      if (!res?.success) {
        throw new Error(res?.detail || res?.message || '上传产物失败')
      }
      setUploadFile(null)
      setVersionNote('')
      toast.success('产物已上传')
      await onReload()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '上传失败')
    } finally {
      setUploadLoading(false)
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
            <p>Stage: <span className="font-semibold">{activeCycle.stage || activeCycle.status}</span></p>
            <p>Status: <span className="font-semibold">{activeCycle.status}</span></p>
            <p>Due: <span className="font-semibold">{formatDate(activeCycle.proof_due_at)}</span></p>
          </div>

          {context.permissions?.can_manage_editors ? (
            <div className="space-y-2 rounded-md border border-border bg-muted/50 p-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Assignments</p>
              <Select value={coordinatorAeId} onValueChange={setCoordinatorAeId}>
                <SelectTrigger className="h-9"><SelectValue placeholder="Coordinator AE" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">-- None --</SelectItem>
                  {staff.map((item) => <SelectItem key={item.id} value={item.id}>{item.name}</SelectItem>)}
                </SelectContent>
              </Select>
              <Select value={typesetterId} onValueChange={setTypesetterId}>
                <SelectTrigger className="h-9"><SelectValue placeholder="Typesetter" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">-- None --</SelectItem>
                  {productionStaff.map((item) => <SelectItem key={item.id} value={item.id}>{item.name}</SelectItem>)}
                </SelectContent>
              </Select>
              <Select value={languageEditorId} onValueChange={setLanguageEditorId}>
                <SelectTrigger className="h-9"><SelectValue placeholder="Language Editor" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">-- None --</SelectItem>
                  {productionStaff.map((item) => <SelectItem key={item.id} value={item.id}>{item.name}</SelectItem>)}
                </SelectContent>
              </Select>
              <Select value={pdfEditorId} onValueChange={setPdfEditorId}>
                <SelectTrigger className="h-9"><SelectValue placeholder="PDF Editor" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">-- None --</SelectItem>
                  {productionStaff.map((item) => <SelectItem key={item.id} value={item.id}>{item.name}</SelectItem>)}
                </SelectContent>
              </Select>

              <Button type="button" variant="outline" onClick={() => void handleUpdateAssignments()} disabled={createLoading}>
                {createLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Update Assignments
              </Button>
            </div>
          ) : null}

          {activeCycle.artifacts && activeCycle.artifacts.length > 0 && (
            <div className="space-y-2 rounded-md border border-border bg-muted/50 p-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Artifacts</p>
              <ul className="text-xs text-muted-foreground space-y-1">
                {activeCycle.artifacts.map(a => (
                  <li key={a.id}>- {a.artifact_kind}: {a.file_name}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="space-y-2 rounded-md border border-border bg-muted/50 p-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Upload Artifact</p>
            <Select value={uploadKind} onValueChange={setUploadKind}>
              <SelectTrigger className="h-9">
                <SelectValue placeholder="Select artifact kind" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="source_manuscript_snapshot">Source Manuscript Snapshot</SelectItem>
                <SelectItem value="typeset_output">Typeset Output</SelectItem>
                <SelectItem value="language_output">Language Output</SelectItem>
                <SelectItem value="ae_internal_proof">AE Internal Proof</SelectItem>
                <SelectItem value="final_confirmation_pdf">Final Confirmation PDF</SelectItem>
                <SelectItem value="publication_pdf">Publication PDF</SelectItem>
              </SelectContent>
            </Select>
            <Input
              type="file"
              onChange={(event) => setUploadFile(event.target.files?.[0] ?? null)}
              className="w-full text-xs"
            />
            <Textarea
              value={versionNote}
              onChange={(event) => setVersionNote(event.target.value)}
              rows={2}
              placeholder="Note"
            />
            <Button
              type="button"
              onClick={() => void handleUploadArtifact()}
              disabled={uploadLoading || !uploadFile}
              className="w-full gap-2"
            >
              {uploadLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
              Upload Artifact
            </Button>
          </div>
          
          <Button
            type="button"
            variant="outline"
            onClick={() => void handleOpenGalley(activeCycle)}
            disabled={!activeCycle.galley_path}
            className="w-full"
          >
            Open Current Galley (Legacy)
          </Button>

        </div>
      )}
    </section>
  )
}
