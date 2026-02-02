/**
 * 作者地理分布图表
 * 功能: 水平条形图展示 Top 10 国家
 *
 * 中文注释:
 * - 按投稿数排序
 * - 使用渐变色区分排名
 */

'use client'

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { GeoData } from '@/types'

interface AuthorGeoChartProps {
  data: GeoData[]
}

// 渐变色数组（从深到浅）
const COLORS = [
  'hsl(var(--primary))',
  'hsl(var(--primary) / 0.9)',
  'hsl(var(--primary) / 0.8)',
  'hsl(var(--primary) / 0.7)',
  'hsl(var(--primary) / 0.6)',
  'hsl(var(--primary) / 0.55)',
  'hsl(var(--primary) / 0.5)',
  'hsl(var(--primary) / 0.45)',
  'hsl(var(--primary) / 0.4)',
  'hsl(var(--primary) / 0.35)',
]

export function AuthorGeoChart({ data }: AuthorGeoChartProps) {
  const chartData = data.map((item) => ({
    country: item.country,
    投稿数: item.submission_count,
  }))

  return (
    <Card>
      <CardHeader>
        <CardTitle>作者地理分布（Top 10）</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={350}>
          <BarChart data={chartData} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis type="number" tick={{ fontSize: 12 }} />
            <YAxis
              type="category"
              dataKey="country"
              tick={{ fontSize: 12 }}
              width={100}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'hsl(var(--background))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '6px',
              }}
            />
            <Bar dataKey="投稿数" radius={[0, 4, 4, 0]}>
              {chartData.map((_, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={COLORS[index] || COLORS[COLORS.length - 1]}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
