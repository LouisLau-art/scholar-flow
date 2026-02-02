/**
 * TanStack Query 客户端配置
 * 功能: 提供全局 QueryClient 实例和 Provider 配置
 *
 * 中文注释:
 * - staleTime: 数据新鲜时间，5分钟内不重新请求
 * - gcTime: 垃圾回收时间，10分钟后清理缓存
 * - retry: 失败重试次数
 * - refetchOnWindowFocus: 窗口获得焦点时不自动刷新（分析数据不需要实时更新）
 */

import { QueryClient } from '@tanstack/react-query'

/**
 * 创建 QueryClient 实例
 * 使用工厂函数确保每个请求获得独立实例（SSR 兼容）
 */
export function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // 分析数据缓存 5 分钟
        staleTime: 5 * 60 * 1000,
        // 缓存保留 10 分钟
        gcTime: 10 * 60 * 1000,
        // 失败重试 1 次
        retry: 1,
        // 窗口获得焦点时不自动刷新
        refetchOnWindowFocus: false,
      },
    },
  })
}

// 浏览器端单例
let browserQueryClient: QueryClient | undefined = undefined

/**
 * 获取 QueryClient 实例
 * 服务端: 每次返回新实例
 * 客户端: 返回单例
 */
export function getQueryClient() {
  if (typeof window === 'undefined') {
    // 服务端: 每次创建新实例
    return makeQueryClient()
  } else {
    // 客户端: 使用单例
    if (!browserQueryClient) {
      browserQueryClient = makeQueryClient()
    }
    return browserQueryClient
  }
}
