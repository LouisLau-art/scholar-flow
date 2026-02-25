'use client'

import { useEffect, useMemo, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { toast } from 'sonner'
import TiptapEditor from '@/components/cms/TiptapEditor'
import { createCmsPage, listCmsPages, updateCmsPage, uploadCmsImage, type CmsPage } from '@/services/cms'

function slugify(input: string): string {
  return input
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9\\s-]/g, '')
    .replace(/\\s+/g, '-')
    .replace(/-+/g, '-')
}

type Props = {
  onPagesLoaded?: (pages: CmsPage[]) => void
}

export default function CmsPagesPanel({ onPagesLoaded }: Props) {
  const [isLoading, setIsLoading] = useState(true)
  const [pages, setPages] = useState<CmsPage[]>([])

  const [newTitle, setNewTitle] = useState('')
  const [newSlug, setNewSlug] = useState('')

  const [selectedSlug, setSelectedSlug] = useState<string | null>(null)
  const selectedPage = useMemo(() => pages.find((p) => p.slug === selectedSlug) || null, [pages, selectedSlug])

  const [editTitle, setEditTitle] = useState('')
  const [editContent, setEditContent] = useState('')
  const [editPublished, setEditPublished] = useState(false)
  const [isSaving, setIsSaving] = useState(false)

  const refresh = async () => {
    setIsLoading(true)
    try {
      const items = await listCmsPages()
      setPages(items)
      onPagesLoaded?.(items)
      if (!selectedSlug && items.length > 0) setSelectedSlug(items[0].slug)
    } catch (e: any) {
      toast.error(e?.message || '加载页面失败')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    refresh()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!selectedPage) return
    setEditTitle(selectedPage.title || '')
    setEditContent((selectedPage.content as string) || '')
    setEditPublished(Boolean(selectedPage.is_published))
  }, [selectedPage])

  const handleCreate = async () => {
    const title = newTitle.trim()
    const slug = newSlug.trim().toLowerCase()
    if (!title || !slug) {
      toast.error('Title 和 Slug 不能为空')
      return
    }
    setIsSaving(true)
    try {
      const created = await createCmsPage({ title, slug, content: '<p></p>', is_published: false })
      toast.success('页面已创建（草稿）')
      setNewTitle('')
      setNewSlug('')
      await refresh()
      setSelectedSlug(created.slug)
    } catch (e: any) {
      toast.error(e?.message || '创建失败')
    } finally {
      setIsSaving(false)
    }
  }

  const handleSave = async () => {
    if (!selectedPage) return
    setIsSaving(true)
    try {
      const updated = await updateCmsPage(selectedPage.slug, {
        title: editTitle,
        content: editContent,
        is_published: editPublished,
      })
      toast.success('已保存')
      setPages((prev) => prev.map((p) => (p.slug === selectedPage.slug ? { ...p, ...updated } : p)))
    } catch (e: any) {
      toast.error(e?.message || '保存失败')
    } finally {
      setIsSaving(false)
    }
  }

  if (isLoading) {
    return (
      <div className="rounded-xl border border-border bg-card p-6 text-muted-foreground">
        Loading CMS pages…
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
      <Card className="lg:col-span-4">
        <CardHeader>
          <CardTitle>Pages</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">Create</div>
            <input
              value={newTitle}
              onChange={(e) => {
                const v = e.target.value
                setNewTitle(v)
                if (!newSlug) setNewSlug(slugify(v))
              }}
              placeholder="Title"
              className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm"
            />
            <input
              value={newSlug}
              onChange={(e) => setNewSlug(slugify(e.target.value))}
              placeholder="Slug (e.g., about)"
              className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm font-mono"
            />
            <Button type="button" onClick={handleCreate} disabled={isSaving}>
              Create Draft
            </Button>
          </div>

          <div className="h-px bg-muted/40" />

          <div className="space-y-2">
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">Existing</div>
            <div className="max-h-[420px] overflow-auto rounded-lg border border-border/60">
              {pages.length === 0 ? (
                <div className="p-4 text-sm text-muted-foreground">No pages yet.</div>
              ) : (
                <ul className="divide-y divide-border/60">
                  {pages.map((page) => (
                    <li key={page.slug}>
                      <button
                        type="button"
                        onClick={() => setSelectedSlug(page.slug)}
                        className={`w-full px-4 py-3 text-left text-sm hover:bg-muted/40 ${
                          selectedSlug === page.slug ? 'bg-muted/40' : 'bg-card'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-foreground">{page.title}</span>
                          <span className={`text-xs font-mono ${page.is_published ? 'text-emerald-600' : 'text-amber-600'}`}>
                            {page.is_published ? 'published' : 'draft'}
                          </span>
                        </div>
                        <div className="text-xs font-mono text-muted-foreground mt-1">{page.slug}</div>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="lg:col-span-8">
        <CardHeader>
          <CardTitle>Editor</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {!selectedPage ? (
            <div className="rounded-xl border border-border bg-muted/40 p-6 text-muted-foreground">
              Select a page to edit.
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
                <div className="md:col-span-2">
                  <label className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">Title</label>
                  <input
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-border bg-card px-3 py-2 text-sm"
                  />
                </div>
                <div className="md:col-span-1">
                  <label className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">Published</label>
                  <div className="mt-2 flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={editPublished}
                      onChange={(e) => setEditPublished(e.target.checked)}
                      className="h-4 w-4"
                    />
                    <span className="text-sm text-foreground">
                      {editPublished ? 'Visible to public' : 'Draft'}
                    </span>
                  </div>
                </div>
              </div>

              <div className="text-xs font-mono text-muted-foreground">
                Public URL: <span className="text-foreground">/journal/{selectedPage.slug}</span>
              </div>

              <TiptapEditor
                value={editContent}
                onChange={setEditContent}
                onUploadImage={uploadCmsImage}
              />

              <div className="flex items-center justify-end gap-3">
                <Button type="button" variant="outline" onClick={refresh} disabled={isSaving}>
                  Refresh
                </Button>
                <Button type="button" onClick={handleSave} disabled={isSaving}>
                  {isSaving ? 'Saving…' : 'Save'}
                </Button>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
