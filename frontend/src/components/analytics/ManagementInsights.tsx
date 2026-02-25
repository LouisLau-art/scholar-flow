'use client'

import Link from 'next/link'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import type {
  EditorEfficiencyItem,
  SLAAlertItem,
  StageDurationItem,
} from '@/types'

const STAGE_LABELS: Record<StageDurationItem['stage'], string> = {
  pre_check: '预审',
  under_review: '外审',
  decision: '终审',
  production: '生产',
}

function getSeverityClass(level: SLAAlertItem['severity']) {
  if (level === 'high') return 'bg-rose-100 text-rose-700 border-rose-200'
  if (level === 'medium') return 'bg-amber-100 text-amber-700 border-amber-200'
  return 'bg-muted text-muted-foreground border-border'
}

type Props = {
  ranking: EditorEfficiencyItem[]
  stageDurations: StageDurationItem[]
  slaAlerts: SLAAlertItem[]
}

export function ManagementInsights(props: Props) {
  const stageChartData = props.stageDurations.map((item) => ({
    stage: STAGE_LABELS[item.stage] || item.stage,
    avgDays: Number(item.avg_days || 0),
    sample: item.sample_size || 0,
  }))

  return (
    <section className="space-y-6">
      <h2 className="text-lg font-semibold">管理视角下钻</h2>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>编辑效率排行</CardTitle>
          </CardHeader>
          <CardContent>
            {props.ranking.length === 0 ? (
              <div className="text-sm text-muted-foreground">暂无可用数据</div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-16">Rank</TableHead>
                    <TableHead>Editor</TableHead>
                    <TableHead className="text-right">处理量</TableHead>
                    <TableHead className="text-right">平均首次决定</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {props.ranking.map((row, idx) => (
                    <TableRow key={row.editor_id}>
                      <TableCell className="font-semibold">{idx + 1}</TableCell>
                      <TableCell>
                        <div className="font-medium text-foreground">{row.editor_name}</div>
                        <div className="text-xs text-muted-foreground">{row.editor_email || '—'}</div>
                      </TableCell>
                      <TableCell className="text-right">{row.handled_count}</TableCell>
                      <TableCell className="text-right">
                        {Number(row.avg_first_decision_days || 0).toFixed(1)} 天
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>阶段耗时分解</CardTitle>
          </CardHeader>
          <CardContent>
            {stageChartData.length === 0 ? (
              <div className="text-sm text-muted-foreground">暂无可用数据</div>
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={stageChartData} margin={{ left: 12, right: 12 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis
                    dataKey="stage"
                    tick={{ fontSize: 12 }}
                  />
                  <YAxis
                    tick={{ fontSize: 12 }}
                    width={48}
                  />
                  <Tooltip
                    formatter={(value) => `${Number(value || 0).toFixed(1)} 天`}
                    contentStyle={{
                      backgroundColor: 'hsl(var(--background))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '6px',
                    }}
                  />
                  <Bar dataKey="avgDays" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>SLA 异常预警</CardTitle>
        </CardHeader>
        <CardContent>
          {props.slaAlerts.length === 0 ? (
            <div className="text-sm text-muted-foreground">暂无超 SLA 稿件</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Manuscript</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Severity</TableHead>
                  <TableHead className="text-right">逾期任务</TableHead>
                  <TableHead className="text-right">最长逾期</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {props.slaAlerts.map((row) => (
                  <TableRow key={row.manuscript_id}>
                    <TableCell>
                      <Link
                        className="font-medium text-foreground hover:text-primary"
                        href={`/editor/manuscript/${row.manuscript_id}`}
                      >
                        {row.title}
                      </Link>
                      <div className="text-xs text-muted-foreground">
                        {row.journal_title || 'Unknown Journal'}
                        {' · '}
                        {row.editor_name || row.owner_name || 'Unassigned'}
                      </div>
                    </TableCell>
                    <TableCell>{row.status}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className={getSeverityClass(row.severity)}>
                        {row.severity.toUpperCase()}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">{row.overdue_tasks_count}</TableCell>
                    <TableCell className="text-right">{Number(row.max_overdue_days || 0).toFixed(1)} 天</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </section>
  )
}
