import DashboardPageClient from '@/components/dashboard/DashboardPageClient'
import { getBackendOrigin } from '@/lib/backend-origin'
import { getServerAccessToken } from '@/lib/server-session'

type DashboardInitialData = {
  initialStats: any | null
  initialSubmissions: any[]
  initialRoles: string[] | null
  initialStatsLoaded: boolean
  initialSubmissionsLoaded: boolean
  initialRolesLoaded: boolean
}

async function fetchJsonWithToken(url: string, token: string): Promise<{ ok: boolean; data: any }> {
  try {
    const res = await fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
      cache: 'no-store',
    })
    if (!res.ok) return { ok: false, data: null }
    const payload = await res.json().catch(() => null)
    if (!payload?.success) return { ok: false, data: null }
    return { ok: true, data: payload.data ?? null }
  } catch {
    return { ok: false, data: null }
  }
}

async function getDashboardInitialData(): Promise<DashboardInitialData> {
  const token = getServerAccessToken()
  if (!token) {
    return {
      initialStats: null,
      initialSubmissions: [],
      initialRoles: null,
      initialStatsLoaded: false,
      initialSubmissionsLoaded: false,
      initialRolesLoaded: false,
    }
  }

  const origin = getBackendOrigin()
  const [statsRes, submissionsRes, profileRes] = await Promise.all([
    fetchJsonWithToken(`${origin}/api/v1/stats/author`, token),
    fetchJsonWithToken(`${origin}/api/v1/manuscripts/mine`, token),
    fetchJsonWithToken(`${origin}/api/v1/user/profile`, token),
  ])

  return {
    initialStats: statsRes.ok ? statsRes.data : null,
    initialSubmissions: submissionsRes.ok && Array.isArray(submissionsRes.data) ? submissionsRes.data : [],
    initialRoles: profileRes.ok && Array.isArray(profileRes.data?.roles) ? profileRes.data.roles : null,
    initialStatsLoaded: statsRes.ok,
    initialSubmissionsLoaded: submissionsRes.ok,
    initialRolesLoaded: profileRes.ok,
  }
}

export default async function DashboardPage() {
  const initialData = await getDashboardInitialData()
  return <DashboardPageClient {...initialData} />
}
