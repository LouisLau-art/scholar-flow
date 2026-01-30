/**
 * 编辑流程图表
 * 功能: 展示状态流水线（漏斗）和决定分布（饼图）
 *
 * 中文注释:
 * - StatusPipelineChart: 漏斗/条形图展示各状态稿件数
 * - DecisionDistributionChart: 饼图展示决定分布
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
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { PipelineData, DecisionData } from '@/types'

// 状态名称映射
const STAGE_LABELS: Record<string, string> = {
  submitted: '已投稿',
  under_review: '审稿中',
  revision: '修改中',
  in_production: '制作中',
}

// 决定类型颜色
const DECISION_COLORS: Record<string, string> = {
  accepted: 'hsl(142, 76%, 36%)', // 绿色
  rejected: 'hsl(0, 84%, 60%)', // 红色
  desk_reject: 'hsl(0, 60%, 50%)', // 深红
  revision: 'hsl(45, 93%, 47%)', // 黄色
}

interface StatusPipelineChartProps {
  data: PipelineData[]
}

/**
 * 状态流水线图表（水平条形图）
 */
export function StatusPipelineChart({ data }: StatusPipelineChartProps) {
  const chartData = data.map((item) => ({
    name: STAGE_LABELS[item.stage] || item.stage,
    数量: item.count,
  }))

  return (
    <Card>
      <CardHeader>
        <CardTitle>稿件状态分布</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={chartData} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis type="number" tick={{ fontSize: 12 }} />
            <YAxis
              type="category"
              dataKey="name"
              tick={{ fontSize: 12 }}
              width={80}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'hsl(var(--background))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '6px',
              }}
            />
            <Bar
              dataKey="数量"
              fill="hsl(var(--primary))"
              radius={[0, 4, 4, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}

interface DecisionDistributionChartProps {
  data: DecisionData[]
}

// 决定类型名称映射
const DECISION_LABELS: Record<string, string> = {
  accepted: '接受',
  rejected: '拒绝',
  desk_reject: 'Desk Reject',
  revision: '修改后重审',
}

/**
 * 决定分布图表（饼图）
 */
export function DecisionDistributionChart({
  data,
}: DecisionDistributionChartProps) {
  const chartData = data.map((item) => ({
    name: DECISION_LABELS[item.decision] || item.decision,
    value: item.count,
    color: DECISION_COLORS[item.decision] || 'hsl(var(--muted))',
  }))

  return (
    <Card>
      <CardHeader>
        <CardTitle>年度决定分布</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={250}>
          <PieChart>
            <Pie
              data={chartData}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius={50}
              outerRadius={80}
              paddingAngle={2}
              label={({ name, percent }) =>
                `${name} ${(percent * 100).toFixed(0)}%`
              }
              labelLine={false}
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                backgroundColor: 'hsl(var(--background))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '6px',
              }}
            />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
