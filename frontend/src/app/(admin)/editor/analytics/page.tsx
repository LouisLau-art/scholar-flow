/**
 * Analytics Dashboard 页面
 * 功能: 主编/编辑分析仪表盘
 *
 * 中文注释:
 * - 展示 KPI 卡片、趋势图表、地理分布
 * - 使用 TanStack Query 获取数据
 * - 需要 EIC/ME 角色权限
 */

'use client'

import { useQuery } from '@tanstack/react-query'
import { AnalyticsApi } from '@/lib/api/analytics'
import { KPIGrid, FinanceKPIRow } from '@/components/analytics/KPISection'
import {
  KPIGridSkeleton,
  FinanceKPISkeleton,
  ChartSkeleton,
} from '@/components/analytics/KPISkeleton'
import { SubmissionTrendChart } from '@/components/analytics/SubmissionTrendChart'
import {
  StatusPipelineChart,
  DecisionDistributionChart,
} from '@/components/analytics/EditorialCharts'
import { AuthorGeoChart } from '@/components/analytics/AuthorGeoChart'
import { ExportButton } from '@/components/analytics/ExportButton'
import { QueryProvider } from '@/components/providers/QueryProvider'
import { BarChart3 } from 'lucide-react'

function AnalyticsDashboardContent() {
  // 获取 KPI 数据
  const {
    data: summaryData,
    isLoading: summaryLoading,
    error: summaryError,
  } = useQuery({
    queryKey: ['analytics', 'summary'],
    queryFn: () => AnalyticsApi.getSummary(),
  })

  // 获取趋势数据
  const {
    data: trendsData,
    isLoading: trendsLoading,
    error: trendsError,
  } = useQuery({
    queryKey: ['analytics', 'trends'],
    queryFn: () => AnalyticsApi.getTrends(),
  })

  // 获取地理数据
  const {
    data: geoData,
    isLoading: geoLoading,
    error: geoError,
  } = useQuery({
    queryKey: ['analytics', 'geo'],
    queryFn: () => AnalyticsApi.getGeo(),
  })

  // 错误处理
  if (summaryError || trendsError || geoError) {
    const error = summaryError || trendsError || geoError
    return (
      <div className="p-6">
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
          <h3 className="font-semibold text-destructive">加载失败</h3>
          <p className="text-sm text-destructive/80">
            {error instanceof Error ? error.message : '请稍后重试'}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <BarChart3 className="h-8 w-8 text-primary" />
          <div>
            <h1 className="text-2xl font-bold">分析仪表盘</h1>
            <p className="text-muted-foreground">期刊运营核心指标概览</p>
          </div>
        </div>
        <ExportButton />
      </div>

      {/* KPI 网格 */}
      <section>
        <h2 className="text-lg font-semibold mb-4">核心指标</h2>
        {summaryLoading ? (
          <KPIGridSkeleton />
        ) : summaryData?.kpi ? (
          <KPIGrid data={summaryData.kpi} />
        ) : null}
      </section>

      {/* 财务 KPI */}
      <section>
        <h2 className="text-lg font-semibold mb-4">财务指标</h2>
        {summaryLoading ? (
          <FinanceKPISkeleton />
        ) : summaryData?.kpi ? (
          <FinanceKPIRow data={summaryData.kpi} />
        ) : null}
      </section>

      {/* 趋势图表 */}
      <section>
        <h2 className="text-lg font-semibold mb-4">投稿趋势</h2>
        {trendsLoading ? (
          <ChartSkeleton height={300} />
        ) : trendsData?.trends && trendsData.trends.length > 0 ? (
          <SubmissionTrendChart data={trendsData.trends} />
        ) : (
          <div className="rounded-lg border p-8 text-center text-muted-foreground">
            暂无趋势数据
          </div>
        )}
      </section>

      {/* 编辑流程图表 */}
      <section className="grid gap-6 md:grid-cols-2">
        <div>
          <h2 className="text-lg font-semibold mb-4">状态分布</h2>
          {trendsLoading ? (
            <ChartSkeleton height={250} />
          ) : trendsData?.pipeline && trendsData.pipeline.length > 0 ? (
            <StatusPipelineChart data={trendsData.pipeline} />
          ) : (
            <div className="rounded-lg border p-8 text-center text-muted-foreground">
              暂无状态数据
            </div>
          )}
        </div>
        <div>
          <h2 className="text-lg font-semibold mb-4">决定分布</h2>
          {trendsLoading ? (
            <ChartSkeleton height={250} />
          ) : trendsData?.decisions && trendsData.decisions.length > 0 ? (
            <DecisionDistributionChart data={trendsData.decisions} />
          ) : (
            <div className="rounded-lg border p-8 text-center text-muted-foreground">
              暂无决定数据
            </div>
          )}
        </div>
      </section>

      {/* 地理分布 */}
      <section>
        <h2 className="text-lg font-semibold mb-4">作者地理分布</h2>
        {geoLoading ? (
          <ChartSkeleton height={350} />
        ) : geoData?.countries && geoData.countries.length > 0 ? (
          <AuthorGeoChart data={geoData.countries} />
        ) : (
          <div className="rounded-lg border p-8 text-center text-muted-foreground">
            暂无地理数据
          </div>
        )}
      </section>
    </div>
  )
}

export default function AnalyticsDashboardPage() {
  return (
    <QueryProvider>
      <AnalyticsDashboardContent />
    </QueryProvider>
  )
}
