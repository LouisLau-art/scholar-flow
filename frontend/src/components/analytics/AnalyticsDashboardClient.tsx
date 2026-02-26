'use client'

import dynamic from 'next/dynamic'
import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, BarChart3 } from 'lucide-react'

import { AnalyticsApi } from '@/lib/api/analytics'
import { KPIGrid, FinanceKPIRow } from '@/components/analytics/KPISection'
import {
  KPIGridSkeleton,
  FinanceKPISkeleton,
  ChartSkeleton,
} from '@/components/analytics/KPISkeleton'
import { ExportButton } from '@/components/analytics/ExportButton'
import { buttonVariants } from '@/components/ui/button'
import { cn } from '@/lib/utils'

const SubmissionTrendChart = dynamic(
  () =>
    import('@/components/analytics/SubmissionTrendChart').then(
      (mod) => mod.SubmissionTrendChart
    ),
  {
    ssr: false,
    loading: () => <ChartSkeleton height={300} />,
  }
)

const StatusPipelineChart = dynamic(
  () =>
    import('@/components/analytics/EditorialCharts').then(
      (mod) => mod.StatusPipelineChart
    ),
  {
    ssr: false,
    loading: () => <ChartSkeleton height={250} />,
  }
)

const DecisionDistributionChart = dynamic(
  () =>
    import('@/components/analytics/EditorialCharts').then(
      (mod) => mod.DecisionDistributionChart
    ),
  {
    ssr: false,
    loading: () => <ChartSkeleton height={250} />,
  }
)

const AuthorGeoChart = dynamic(
  () =>
    import('@/components/analytics/AuthorGeoChart').then(
      (mod) => mod.AuthorGeoChart
    ),
  {
    ssr: false,
    loading: () => <ChartSkeleton height={350} />,
  }
)

const ManagementInsights = dynamic(
  () =>
    import('@/components/analytics/ManagementInsights').then(
      (mod) => mod.ManagementInsights
    ),
  {
    ssr: false,
    loading: () => (
      <div className="grid gap-4 md:grid-cols-2">
        <ChartSkeleton height={260} />
        <ChartSkeleton height={260} />
      </div>
    ),
  }
)

export function AnalyticsDashboardClient() {
  const {
    data: summaryData,
    isLoading: summaryLoading,
    error: summaryError,
  } = useQuery({
    queryKey: ['analytics', 'summary'],
    queryFn: () => AnalyticsApi.getSummary(),
  })

  const {
    data: trendsData,
    isLoading: trendsLoading,
    error: trendsError,
  } = useQuery({
    queryKey: ['analytics', 'trends'],
    queryFn: () => AnalyticsApi.getTrends(),
  })

  const {
    data: geoData,
    isLoading: geoLoading,
    error: geoError,
  } = useQuery({
    queryKey: ['analytics', 'geo'],
    queryFn: () => AnalyticsApi.getGeo(),
  })

  const {
    data: managementData,
    isLoading: managementLoading,
    error: managementError,
  } = useQuery({
    queryKey: ['analytics', 'management'],
    queryFn: () => AnalyticsApi.getManagement({ rankingLimit: 10, slaLimit: 20 }),
  })

  if (summaryError || trendsError || geoError || managementError) {
    const error = summaryError || trendsError || geoError || managementError
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
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <div className="mt-1 rounded-xl bg-card p-2 shadow-sm ring-1 ring-border">
            <BarChart3 className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h1 className="text-3xl font-serif font-bold text-foreground tracking-tight">Analytics</h1>
            <p className="mt-1 text-muted-foreground font-medium">期刊运营核心指标概览</p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Link
            href="/dashboard"
            className={cn(buttonVariants({ variant: 'outline' }), 'gap-2')}
          >
            <ArrowLeft className="h-4 w-4" />
            返回编辑台
          </Link>
          <ExportButton />
        </div>
      </div>

      <section>
        <h2 className="text-lg font-semibold mb-4">核心指标</h2>
        {summaryLoading ? (
          <KPIGridSkeleton />
        ) : summaryData?.kpi ? (
          <KPIGrid data={summaryData.kpi} />
        ) : null}
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-4">财务指标</h2>
        {summaryLoading ? (
          <FinanceKPISkeleton />
        ) : summaryData?.kpi ? (
          <FinanceKPIRow data={summaryData.kpi} />
        ) : null}
      </section>

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

      <section>
        {managementLoading ? (
          <div className="grid gap-4 md:grid-cols-2">
            <ChartSkeleton height={260} />
            <ChartSkeleton height={260} />
          </div>
        ) : (
          <ManagementInsights
            ranking={managementData?.editor_ranking || []}
            stageDurations={managementData?.stage_durations || []}
            slaAlerts={managementData?.sla_alerts || []}
          />
        )}
      </section>
    </div>
  )
}
