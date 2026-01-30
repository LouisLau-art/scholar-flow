'use client'

import { useEffect, useMemo, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { toast } from 'sonner'
import { getCmsMenu, updateCmsMenu, type CmsMenuItemInput, type CmsPage } from '@/services/cms'

type MenuItemState = {
  label: string
  type: 'page' | 'url'
  pageSlug?: string
  url?: string
}

function toInput(items: MenuItemState[]): CmsMenuItemInput[] {
  return items.map((i) => ({
    label: i.label,
    url: i.type === 'url' ? i.url : undefined,
    page_slug: i.type === 'page' ? i.pageSlug : undefined,
    children: [],
  }))
}

function fromApi(items: any[]): MenuItemState[] {
  return (items || [])
    .map((i) => {
      if (i?.page_slug) {
        return { label: String(i.label || ''), type: 'page' as const, pageSlug: String(i.page_slug) }
      }
      return { label: String(i.label || ''), type: 'url' as const, url: String(i.url || '') }
    })
    .filter((i) => i.label.trim() !== '')
}

type Props = {
  pages: CmsPage[]
}

export default function CmsMenuPanel({ pages }: Props) {
  const [isLoading, setIsLoading] = useState(true)
  const [headerItems, setHeaderItems] = useState<MenuItemState[]>([])
  const [footerItems, setFooterItems] = useState<MenuItemState[]>([])
  const [isSaving, setIsSaving] = useState(false)

  const pageSlugs = useMemo(() => pages.map((p) => p.slug).sort(), [pages])

  const load = async () => {
    setIsLoading(true)
    try {
      const header = await getCmsMenu('header')
      const footer = await getCmsMenu('footer')
      setHeaderItems(fromApi(header))
      setFooterItems(fromApi(footer))
    } catch (e: any) {
      toast.error(e?.message || '加载菜单失败')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const move = (items: MenuItemState[], index: number, delta: number) => {
    const next = [...items]
    const target = next[index]
    const newIndex = index + delta
    if (newIndex < 0 || newIndex >= next.length) return next
    next.splice(index, 1)
    next.splice(newIndex, 0, target)
    return next
  }

  const saveLocation = async (location: 'header' | 'footer') => {
    setIsSaving(true)
    try {
      const items = location === 'header' ? headerItems : footerItems
      await updateCmsMenu({ location, items: toInput(items) })
      toast.success('菜单已保存')
      await load()
    } catch (e: any) {
      toast.error(e?.message || '保存失败')
    } finally {
      setIsSaving(false)
    }
  }

  const renderList = (location: 'header' | 'footer', items: MenuItemState[], setItems: (v: MenuItemState[]) => void) => (
    <div className="space-y-3">
      {items.length === 0 ? (
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
          No items yet. Add one below.
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((item, idx) => (
            <div key={`${location}-${idx}`} className="rounded-xl border border-slate-200 bg-white p-4">
              <div className="grid grid-cols-1 gap-3 md:grid-cols-12">
                <div className="md:col-span-4">
                  <label className="text-xs font-semibold text-slate-500 uppercase tracking-widest">Label</label>
                  <input
                    value={item.label}
                    onChange={(e) => {
                      const v = e.target.value
                      setItems(items.map((x, i) => (i === idx ? { ...x, label: v } : x)))
                    }}
                    className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
                  />
                </div>

                <div className="md:col-span-3">
                  <label className="text-xs font-semibold text-slate-500 uppercase tracking-widest">Type</label>
                  <select
                    value={item.type}
                    onChange={(e) => {
                      const type = e.target.value as MenuItemState['type']
                      setItems(items.map((x, i) => (i === idx ? { label: x.label, type } : x)))
                    }}
                    className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
                  >
                    <option value="page">Internal Page</option>
                    <option value="url">External URL</option>
                  </select>
                </div>

                <div className="md:col-span-5">
                  {item.type === 'page' ? (
                    <>
                      <label className="text-xs font-semibold text-slate-500 uppercase tracking-widest">Page</label>
                      <select
                        value={item.pageSlug || ''}
                        onChange={(e) => {
                          const pageSlug = e.target.value
                          setItems(items.map((x, i) => (i === idx ? { ...x, pageSlug } : x)))
                        }}
                        className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-mono"
                      >
                        <option value="" disabled>
                          Select…
                        </option>
                        {pageSlugs.map((slug) => (
                          <option key={slug} value={slug}>
                            {slug}
                          </option>
                        ))}
                      </select>
                      <div className="mt-1 text-xs font-mono text-slate-500">
                        URL: {item.pageSlug ? `/journal/${item.pageSlug}` : '—'}
                      </div>
                    </>
                  ) : (
                    <>
                      <label className="text-xs font-semibold text-slate-500 uppercase tracking-widest">URL</label>
                      <input
                        value={item.url || ''}
                        onChange={(e) => {
                          const url = e.target.value
                          setItems(items.map((x, i) => (i === idx ? { ...x, url } : x)))
                        }}
                        placeholder="https://example.com or /submit"
                        className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-mono"
                      />
                    </>
                  )}
                </div>
              </div>

              <div className="mt-3 flex items-center justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => setItems(move(items, idx, -1))} disabled={idx === 0 || isSaving}>
                  Up
                </Button>
                <Button type="button" variant="outline" onClick={() => setItems(move(items, idx, 1))} disabled={idx === items.length - 1 || isSaving}>
                  Down
                </Button>
                <Button
                  type="button"
                  variant="destructive"
                  onClick={() => setItems(items.filter((_x, i) => i !== idx))}
                  disabled={isSaving}
                >
                  Remove
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="flex items-center gap-3">
        <Button
          type="button"
          variant="outline"
          onClick={() => setItems([...items, { label: 'New Item', type: 'page', pageSlug: pageSlugs[0] }])}
          disabled={isSaving || pageSlugs.length === 0}
        >
          Add Item
        </Button>
        <div className="flex-1" />
        <Button type="button" onClick={() => saveLocation(location)} disabled={isSaving}>
          {isSaving ? 'Saving…' : `Save ${location}`}
        </Button>
      </div>
    </div>
  )

  return (
    <div className="space-y-6">
      {isLoading ? (
        <div className="rounded-xl border border-slate-200 bg-white p-6 text-slate-600">
          Loading menus…
        </div>
      ) : (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Header Menu</CardTitle>
            </CardHeader>
            <CardContent>{renderList('header', headerItems, setHeaderItems)}</CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Footer Menu</CardTitle>
            </CardHeader>
            <CardContent>{renderList('footer', footerItems, setFooterItems)}</CardContent>
          </Card>
        </>
      )}
    </div>
  )
}

