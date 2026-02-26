import { authService } from '@/services/auth'

const CMS_MENU_CACHE_TTL_MS = 60_000
const cmsMenuCache = new Map<string, { expiresAt: number; data: any }>()
const cmsMenuInflight = new Map<string, Promise<any>>()

export type CmsPage = {
  id: string
  slug: string
  title: string
  content?: string | null
  is_published: boolean
  updated_at?: string
  created_at?: string
}

export type CmsMenuItemInput = {
  label: string
  url?: string | null
  page_slug?: string | null
  children?: CmsMenuItemInput[]
}

export type CmsMenuUpdateRequest = {
  location: 'header' | 'footer'
  items: CmsMenuItemInput[]
}

async function requireToken(): Promise<string> {
  const token = await authService.getAccessToken()
  if (!token) throw new Error('Missing access token')
  return token
}

export async function listCmsPages(): Promise<CmsPage[]> {
  const token = await requireToken()
  const res = await fetch('/api/v1/cms/pages', {
    headers: { Authorization: `Bearer ${token}` },
  })
  const body = await res.json()
  if (!res.ok || !body?.success) throw new Error(body?.detail || 'Failed to list pages')
  return body.data as CmsPage[]
}

export async function createCmsPage(payload: { title: string; slug: string; content?: string; is_published?: boolean }): Promise<CmsPage> {
  const token = await requireToken()
  const res = await fetch('/api/v1/cms/pages', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  })
  const body = await res.json()
  if (!res.ok || !body?.success) throw new Error(body?.detail || body?.message || 'Failed to create page')
  return body.data as CmsPage
}

export async function updateCmsPage(slug: string, patch: Partial<Pick<CmsPage, 'title' | 'content' | 'is_published'>>): Promise<CmsPage> {
  const token = await requireToken()
  const res = await fetch(`/api/v1/cms/pages/${encodeURIComponent(slug)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify(patch),
  })
  const body = await res.json()
  if (!res.ok || !body?.success) throw new Error(body?.detail || body?.message || 'Failed to update page')
  return body.data as CmsPage
}

export async function uploadCmsImage(file: File): Promise<string> {
  const token = await requireToken()
  const form = new FormData()
  form.append('file', file)
  const res = await fetch('/api/v1/cms/upload', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  })
  const body = await res.json()
  if (!res.ok || !body?.success) throw new Error(body?.detail || 'Failed to upload image')
  return body.data?.url as string
}

export async function getCmsMenu(location?: 'header' | 'footer'): Promise<any> {
  const cacheKey = `menu:${location || 'all'}`
  const now = Date.now()
  const cached = cmsMenuCache.get(cacheKey)
  if (cached && cached.expiresAt > now) {
    return cached.data
  }
  const inflight = cmsMenuInflight.get(cacheKey)
  if (inflight) {
    return inflight
  }

  const url = location ? `/api/v1/cms/menu?location=${location}` : '/api/v1/cms/menu'
  const requestPromise = (async () => {
    const res = await fetch(url)
    const body = await res.json()
    if (!res.ok || !body?.success) throw new Error(body?.detail || 'Failed to load menu')
    const data = body.data
    cmsMenuCache.set(cacheKey, {
      expiresAt: Date.now() + CMS_MENU_CACHE_TTL_MS,
      data,
    })
    return data
  })()
  cmsMenuInflight.set(cacheKey, requestPromise)
  try {
    return await requestPromise
  } finally {
    if (cmsMenuInflight.get(cacheKey) === requestPromise) {
      cmsMenuInflight.delete(cacheKey)
    }
  }
}

export async function updateCmsMenu(payload: CmsMenuUpdateRequest): Promise<any> {
  const token = await requireToken()
  const res = await fetch('/api/v1/cms/menu', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  })
  const body = await res.json()
  if (!res.ok || !body?.success) throw new Error(body?.detail || 'Failed to update menu')
  cmsMenuCache.clear()
  cmsMenuInflight.clear()
  return body.data
}
