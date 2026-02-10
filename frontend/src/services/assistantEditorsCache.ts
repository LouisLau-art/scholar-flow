import { EditorApi } from '@/services/editorApi'

export type AssistantEditorOption = {
  id: string
  full_name?: string | null
  email?: string | null
}

const AE_CACHE_TTL_MS = 5 * 60 * 1000

let cache: { data: AssistantEditorOption[]; cachedAt: number } | null = null
let inflight: Promise<AssistantEditorOption[]> | null = null

function isCacheFresh() {
  return Boolean(cache && Date.now() - cache.cachedAt < AE_CACHE_TTL_MS)
}

export function peekAssistantEditorsCache(): AssistantEditorOption[] | null {
  if (!isCacheFresh() || !cache) return null
  return cache.data
}

export async function getAssistantEditors(options?: { force?: boolean }): Promise<AssistantEditorOption[]> {
  const force = Boolean(options?.force)
  if (!force && isCacheFresh() && cache) {
    return cache.data
  }

  if (inflight) return inflight

  inflight = (async () => {
    const res = await EditorApi.listAssistantEditors()
    if (!res?.success) {
      throw new Error(res?.detail || res?.message || 'Failed to load assistant editors')
    }
    const rows = (res.data || []) as AssistantEditorOption[]
    cache = { data: rows, cachedAt: Date.now() }
    return rows
  })()

  try {
    return await inflight
  } finally {
    inflight = null
  }
}

