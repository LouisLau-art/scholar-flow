import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { authService } from '@/services/auth'
import { User } from '@/types/user'
import { toast } from 'sonner'

async function fetchProfile(): Promise<User | null> {
  const token = await authService.getAccessToken()
  if (!token) return null

  const res = await fetch('/api/v1/user/profile', {
    headers: { Authorization: `Bearer ${token}` },
  })

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
    const error = await res.json().catch(() => ({}))
    throw new Error(error.detail || 'Failed to update profile')
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
    throw new Error(error.detail || 'Failed to update password')
  }
}

export function useProfile() {
  const queryClient = useQueryClient()

  const { data: profile, isLoading, error } = useQuery({
    queryKey: ['user-profile'],
    queryFn: fetchProfile,
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
