/**
 * KPI Skeleton 组件
 * 功能: KPI 卡片的加载骨架屏
 *
 * 中文注释:
 * - 与 KPIGrid 布局一致
 * - 使用 Tailwind animate-pulse 实现脉冲动画
 */

'use client'

import { Card, CardContent, CardHeader } from '@/components/ui/card'

/**
 * 单个 KPI 卡片骨架
 */
function KPICardSkeleton() {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div className="h-4 w-24 bg-muted animate-pulse rounded" />
        <div className="h-4 w-4 bg-muted animate-pulse rounded" />
      </CardHeader>
      <CardContent>
        <div className="h-8 w-20 bg-muted animate-pulse rounded mb-2" />
        <div className="h-3 w-32 bg-muted animate-pulse rounded" />
      </CardContent>
    </Card>
  )
}

/**
 * KPI 网格骨架
 */
export function KPIGridSkeleton() {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <KPICardSkeleton />
      <KPICardSkeleton />
      <KPICardSkeleton />
      <KPICardSkeleton />
    </div>
  )
}

/**
 * 财务 KPI 骨架
 */
export function FinanceKPISkeleton() {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <KPICardSkeleton />
      <KPICardSkeleton />
    </div>
  )
}

/**
 * 图表骨架
 */
export function ChartSkeleton({ height = 300 }: { height?: number }) {
  const heightClass =
    {
      250: 'h-[250px]',
      260: 'h-[260px]',
      300: 'h-[300px]',
      350: 'h-[350px]',
    }[height] ?? 'h-[300px]'

  return (
    <Card>
      <CardHeader>
        <div className="h-5 w-32 bg-muted animate-pulse rounded" />
      </CardHeader>
      <CardContent>
        <div className={`w-full bg-muted animate-pulse rounded ${heightClass}`} />
      </CardContent>
    </Card>
  )
}
