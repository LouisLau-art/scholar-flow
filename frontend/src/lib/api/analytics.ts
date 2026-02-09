/**
 * Analytics API Client
 * 功能: 封装分析仪表盘的 API 调用
 *
 * 中文注释:
 * - 所有函数返回 Promise，用于 TanStack Query
 * - 自动从 Supabase session 获取 JWT token
 * - 遵循章程: 禁止在页面组件中直接书写复杂的 API 请求逻辑
 */

import type {
  AnalyticsManagementResponse,
  AnalyticsSummaryResponse,
  TrendsResponse,
  GeoResponse,
} from '@/types'
import { supabase } from '@/lib/supabase'

// API 基础路径
// 中文注释:
// - 统一使用相对路径 `/api/v1/*`，依赖 Next.js rewrites 代理到后端。
// - 这样在本地（:3000 -> :8000）和 Vercel（-> Render）都不需要改业务代码。
const API_BASE = ''

/**
 * 获取当前用户的 JWT token
 */
async function getAuthToken(): Promise<string | null> {
  const {
    data: { session },
  } = await supabase.auth.getSession()
  return session?.access_token || null
}

/**
 * 带认证的 fetch 请求
 */
async function fetchWithAuth<T>(endpoint: string): Promise<T> {
  const token = await getAuthToken()

  if (!token) {
    throw new Error('未登录，请先登录')
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || `请求失败: ${response.status}`)
  }

  return response.json()
}

/**
 * Analytics API 客户端
 */
export const AnalyticsApi = {
  /**
   * 获取 KPI 汇总数据
   */
  async getSummary(): Promise<AnalyticsSummaryResponse> {
    return fetchWithAuth<AnalyticsSummaryResponse>('/api/v1/analytics/summary')
  },

  /**
   * 获取趋势数据（投稿趋势、流水线、决定分布）
   */
  async getTrends(): Promise<TrendsResponse> {
    return fetchWithAuth<TrendsResponse>('/api/v1/analytics/trends')
  },

  /**
   * 获取地理分布数据
   */
  async getGeo(): Promise<GeoResponse> {
    return fetchWithAuth<GeoResponse>('/api/v1/analytics/geo')
  },

  /**
   * 获取管理视角数据（编辑效率 / 阶段耗时 / SLA 预警）
   */
  async getManagement(params?: {
    rankingLimit?: number
    slaLimit?: number
  }): Promise<AnalyticsManagementResponse> {
    const search = new URLSearchParams()
    if (params?.rankingLimit) search.set('ranking_limit', String(params.rankingLimit))
    if (params?.slaLimit) search.set('sla_limit', String(params.slaLimit))
    const suffix = search.toString() ? `?${search.toString()}` : ''
    return fetchWithAuth<AnalyticsManagementResponse>(`/api/v1/analytics/management${suffix}`)
  },

  /**
   * 导出分析报告
   * @param format 导出格式: 'xlsx' 或 'csv'
   */
  async exportReport(format: 'xlsx' | 'csv' = 'xlsx'): Promise<Blob> {
    const token = await getAuthToken()

    if (!token) {
      throw new Error('未登录，请先登录')
    }

    const response = await fetch(
      `${API_BASE}/api/v1/analytics/export?format=${format}`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      },
    )

    if (!response.ok) {
      throw new Error(`导出失败: ${response.status}`)
    }

    return response.blob()
  },
}
