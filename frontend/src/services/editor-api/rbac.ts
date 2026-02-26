import type { CachedGetOptions, EditorRbacContextResponse } from './types'

type RbacApiDeps = {
  authedFetch: (input: RequestInfo, init?: RequestInit) => Promise<Response>
  authedGetJsonCached: <T = any>(url: string, options?: CachedGetOptions) => Promise<T>
}

export function createRbacApi(deps: RbacApiDeps) {
  const { authedFetch, authedGetJsonCached } = deps

  return {
    async listJournals() {
      const res = await authedFetch('/api/v1/editor/journals')
      return res.json()
    },

    async getRbacContext(options?: CachedGetOptions): Promise<EditorRbacContextResponse> {
      return authedGetJsonCached('/api/v1/editor/rbac/context', options)
    },

    async listInternalStaff(
      search?: string,
      options?: { excludeCurrentUser?: boolean },
      cacheOptions?: CachedGetOptions
    ) {
      const params = new URLSearchParams()
      if (search) params.set('search', search)
      if (options?.excludeCurrentUser) params.set('exclude_current_user', 'true')
      const qs = params.toString()
      return authedGetJsonCached(`/api/v1/editor/internal-staff${qs ? `?${qs}` : ''}`, cacheOptions)
    },

    // Feature 044: Pre-check role workflow
    async listAssistantEditors(search?: string) {
      const qs = search ? `?search=${encodeURIComponent(search)}` : ''
      const res = await authedFetch(`/api/v1/editor/assistant-editors${qs}`)
      return res.json()
    },
  }
}
