/**
 * 投稿趋势图表
 * 功能: 使用 Recharts 展示过去 12 个月的投稿和接受趋势
 *
 * 中文注释:
 * - 折线图展示投稿数和接受数
 * - 使用 ScholarFlow 品牌色
 * - 响应式设计
 */

'use client'

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { TrendData } from '@/types'

interface SubmissionTrendChartProps {
  data: TrendData[]
}

/**
 * 格式化月份显示
 */
function formatMonth(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', { month: 'short' })
}

export function SubmissionTrendChart({ data }: SubmissionTrendChartProps) {
  // 格式化数据用于图表
  const chartData = data.map((item) => ({
    month: formatMonth(item.month),
    投稿数: item.submission_count,
    接受数: item.acceptance_count,
  }))

  return (
    <Card>
      <CardHeader>
        <CardTitle>投稿趋势（过去 12 个月）</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis
              dataKey="month"
              tick={{ fontSize: 12 }}
              className="text-muted-foreground"
            />
            <YAxis tick={{ fontSize: 12 }} className="text-muted-foreground" />
            <Tooltip
              contentStyle={{
                backgroundColor: 'hsl(var(--background))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '6px',
              }}
            />
            <Legend />
            {/* 投稿数 - 主色 */}
            <Line
              type="monotone"
              dataKey="投稿数"
              stroke="hsl(var(--primary))"
              strokeWidth={2}
              dot={{ fill: 'hsl(var(--primary))' }}
              activeDot={{ r: 6 }}
            />
            {/* 接受数 - 次色 */}
            <Line
              type="monotone"
              dataKey="接受数"
              stroke="hsl(var(--chart-2))"
              strokeWidth={2}
              dot={{ fill: 'hsl(var(--chart-2))' }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
