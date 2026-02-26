import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { authService } from '@/services/auth'
import { User } from '@/types/user'
import { toast } from 'sonner'

const PROFILE_QUERY_STALE_TIME_MS = 60_000
const PROFILE_QUERY_GC_TIME_MS = 10 * 60_000

async function requestProfile(token: string): Promise<Response> {
  return fetch('/api/v1/user/profile', {
    headers: { Authorization: `Bearer ${token}` },
  })
}

async function fetchProfile(): Promise<User | null> {
  const token = await authService.getAccessToken()
  if (!token) return null

  let res = await requestProfile(token)
  if (res.status === 401) {
    const refreshed = await authService.forceRefreshAccessToken()
    if (refreshed) {
      res = await requestProfile(refreshed)
    }
  }

  if (!res.ok) {
    if (res.status === 401) {
      // Token exists but session is dead (e.g. password changed)
      await authService.signOut()
      window.location.href = '/login?error=session_expired'
      return null
    }
    throw new Error('Failed to fetch profile')
  }

  const data = await res.json()
  if (!data.success) throw new Error(data.message || 'Failed to fetch profile')
  
  return data.data
}

async function updateProfile(data: Partial<User>): Promise<User> {
  const token = await authService.getAccessToken()
  if (!token) throw new Error('Not authenticated')

  const res = await fetch('/api/v1/user/profile', {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  })

  if (!res.ok) {
    if (res.status === 401) {
      await authService.signOut()
      window.location.href = '/login?error=session_expired'
      throw new Error('会话已过期，请重新登录')
    }
    const error = await res.json().catch(() => ({}))
    let errorMessage: unknown = error.detail ?? error.message ?? '更新失败'

    if (Array.isArray(errorMessage)) {
      errorMessage = errorMessage
        .map((e: any) => {
          const loc = Array.isArray(e?.loc) ? e.loc : []
          const fieldKey = loc[loc.length - 1]
          const fieldLabel =
            fieldKey === 'orcid_id'
              ? 'ORCID iD'
              : fieldKey === 'google_scholar_url'
                ? 'Google Scholar URL'
                : fieldKey === 'avatar_url'
                  ? 'Avatar URL'
                  : fieldKey || '表单字段'

          const msg = String(e?.msg ?? '输入不合法')
          if (fieldKey === 'orcid_id') {
            return `${fieldLabel}：格式不正确（示例：0000-0000-0000-0000），也可以留空`
          }
          if (fieldKey === 'google_scholar_url') {
            return `${fieldLabel}：不是有效链接，也可以留空`
          }
          return `${fieldLabel}：${msg}`
        })
        .join('；')
    } else if (typeof errorMessage === 'object' && errorMessage !== null) {
      errorMessage = JSON.stringify(errorMessage)
    } else {
      errorMessage = String(errorMessage)
    }

    const message = typeof errorMessage === 'string' ? errorMessage : String(errorMessage)
    throw new Error(message)
  }

  const result = await res.json()
  return result.data
}

async function updatePassword(password: string): Promise<void> {
  const token = await authService.getAccessToken()
  if (!token) throw new Error('Not authenticated')

  const res = await fetch('/api/v1/user/security/password', {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ password, confirm_password: password }),
  })

  if (!res.ok) {
    const error = await res.json().catch(() => ({}))
    let errorMessage = error.detail || 'Failed to update password'
    if (Array.isArray(errorMessage)) {
      errorMessage = errorMessage.map((e: any) => e.msg).join(', ')
    } else if (typeof errorMessage === 'object') {
      errorMessage = JSON.stringify(errorMessage)
    }
    throw new Error(errorMessage)
  }
}

export function useProfile(options?: { enabled?: boolean }) {
  const queryClient = useQueryClient()
  const enabled = options?.enabled ?? true

  const { data: profile, isLoading, error } = useQuery({
    queryKey: ['user-profile'],
    queryFn: fetchProfile,
    enabled,
    staleTime: PROFILE_QUERY_STALE_TIME_MS,
    gcTime: PROFILE_QUERY_GC_TIME_MS,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    retry: false,
  })

  const { mutate: saveProfile, isPending: isSaving } = useMutation({
    mutationFn: updateProfile,
    onSuccess: (updatedProfile) => {
      queryClient.setQueryData(['user-profile'], updatedProfile)
      toast.success('Profile updated successfully')
    },
    onError: (err) => {
      toast.error(err.message)
    },
  })

  const { mutateAsync: changePassword } = useMutation({
    mutationFn: updatePassword,
    onSuccess: () => {
      toast.success('Password updated successfully. Please sign in again.')
      // Sign out and redirect to login
      setTimeout(() => {
        authService.signOut().then(() => {
          window.location.href = '/login'
        })
      }, 2000)
    },
    onError: (err) => {
      toast.error(err.message)
    },
  })

  return {
    profile,
    isLoading,
    error,
    saveProfile,
    isSaving,
    changePassword,
  }
}
