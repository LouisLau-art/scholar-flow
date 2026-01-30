import { authService } from '@/services/auth'

export interface DOITask {
  id: string
  registration_id: string
  task_type: 'register' | 'update'
  status: 'pending' | 'processing' | 'completed' | 'failed'
  attempts: number
  max_attempts: number
  run_at: string
  last_error?: string
  created_at: string
  completed_at?: string
}

export interface DOITaskListResponse {
  items: DOITask[]
  total: number
  limit: number
  offset: number
}

async function getHeaders() {
  const token = await authService.getAccessToken()
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  }
}

export const doiApi = {
  getTasks: async (status?: string, limit = 20, offset = 0): Promise<DOITaskListResponse> => {
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
    })
    if (status) params.append('status', status)
    
    const headers = await getHeaders()
    const res = await fetch(`/api/v1/doi/tasks?${params.toString()}`, { headers })
    if (!res.ok) throw new Error('Failed to fetch tasks')
    return res.json()
  },

  getFailedTasks: async (limit = 20, offset = 0): Promise<DOITaskListResponse> => {
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
    })
    
    const headers = await getHeaders()
    const res = await fetch(`/api/v1/doi/tasks/failed?${params.toString()}`, { headers })
    if (!res.ok) throw new Error('Failed to fetch failed tasks')
    return res.json()
  },

  retryTask: async (articleId: string) => {
    const headers = await getHeaders()
    const res = await fetch(`/api/v1/doi/${articleId}/retry`, { 
      method: 'POST',
      headers 
    })
    if (!res.ok) throw new Error('Failed to retry task')
    return res.json()
  }
}
