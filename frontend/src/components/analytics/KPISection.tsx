/**
 * KPI Section 组件
 * 功能: 展示 4 个核心 KPI 卡片
 *
 * 中文注释:
 * - KPICard: 单个 KPI 卡片组件
 * - KPIGrid: 4 卡片网格布局
 * - 使用 Shadcn Card 组件，遵循设计规范
 */

'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { FileText, Clock, CheckCircle, DollarSign } from 'lucide-react'
import type { KPISummary } from '@/types'

interface KPICardProps {
  title: string
  value: string | number
  subtitle?: string
  icon: React.ReactNode
  trend?: {
    value: number
    isPositive: boolean
  }
}

/**
 * 单个 KPI 卡片
 */
function KPICard({ title, value, subtitle, icon, trend }: KPICardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        <div className="h-4 w-4 text-muted-foreground">{icon}</div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {subtitle && (
          <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>
        )}
        {trend && (
          <p
            className={`text-xs mt-1 ${trend.isPositive ? 'text-green-600' : 'text-red-600'}`}
          >
            {trend.isPositive ? '↑' : '↓'} {Math.abs(trend.value)}% vs 上月
          </p>
        )}
      </CardContent>
    </Card>
  )
}

interface KPIGridProps {
  data: KPISummary
}

/**
 * KPI 网格布局
 * 展示 4 个核心指标
 */
export function KPIGrid({ data }: KPIGridProps) {
  // 格式化接受率为百分比
  const acceptanceRate = (data.yearly_acceptance_rate * 100).toFixed(1)

  // 格式化金额
  const formatCurrency = (amount: number) => {
    if (amount >= 1000) {
      return `$${(amount / 1000).toFixed(1)}k`
    }
    return `$${amount.toFixed(0)}`
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <KPICard
        title="本月新投稿"
        value={data.new_submissions_month}
        icon={<FileText className="h-4 w-4" />}
      />
      <KPICard
        title="待处理稿件"
        value={data.total_pending}
        icon={<Clock className="h-4 w-4" />}
      />
      <KPICard
        title="平均首次决定时间"
        value={`${data.avg_first_decision_days.toFixed(1)} 天`}
        subtitle="排除 Desk Reject"
        icon={<Clock className="h-4 w-4" />}
      />
      <KPICard
        title="年度接受率"
        value={`${acceptanceRate}%`}
        icon={<CheckCircle className="h-4 w-4" />}
      />
    </div>
  )
}

/**
 * 财务 KPI 行
 * 展示 APC 收入相关指标
 */
export function FinanceKPIRow({ data }: KPIGridProps) {
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount)
  }

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <KPICard
        title="本月 APC 收入"
        value={formatCurrency(data.apc_revenue_month)}
        icon={<DollarSign className="h-4 w-4" />}
      />
      <KPICard
        title="年度 APC 收入"
        value={formatCurrency(data.apc_revenue_year)}
        icon={<DollarSign className="h-4 w-4" />}
      />
    </div>
  )
}
