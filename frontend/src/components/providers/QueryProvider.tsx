/**
 * TanStack Query Provider
 * 功能: 为应用提供 React Query 上下文
 *
 * 中文注释:
 * - 客户端组件
 * - 在 layout 中包裹需要数据查询的页面
 */

'use client'

import { QueryClientProvider } from '@tanstack/react-query'
import { getQueryClient } from '@/lib/query-client'

interface QueryProviderProps {
  children: React.ReactNode
}

export function QueryProvider({ children }: QueryProviderProps) {
  const queryClient = getQueryClient()

  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}
