import React from 'react'

type BackendCoverage = {
  line_rate: number
  branch_rate: number
}

type FrontendCoverage = {
  statement_rate: number
  function_rate: number
  branch_rate: number
}

type Thresholds = {
  backend_ok?: boolean | null
  frontend_ok?: boolean | null
  overall_ok?: boolean | null
}

type CoverageDashboardProps = {
  backend?: BackendCoverage | null
  frontend?: FrontendCoverage | null
  thresholds?: Thresholds | null
}

const formatRate = (value?: number) => (typeof value === 'number' ? `${value.toFixed(2)}%` : '未生成')

const formatStatus = (value?: boolean | null) => {
  if (value === null || value === undefined) return '未校验'
  return value ? '达标' : '未达标'
}

export default function CoverageDashboard({ backend, frontend, thresholds }: CoverageDashboardProps) {
  return (
    <section className="space-y-4" data-testid="coverage-dashboard">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-foreground">测试覆盖率</h2>
        <span className="text-sm text-muted-foreground">总体状态：{formatStatus(thresholds?.overall_ok)}</span>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-xl border border-border bg-card p-4 shadow-sm" data-testid="coverage-backend">
          <h3 className="text-sm font-semibold text-foreground">后端覆盖率</h3>
          <div className="mt-3 space-y-1 text-sm text-muted-foreground">
            <div>行覆盖率：{formatRate(backend?.line_rate)}</div>
            <div>分支覆盖率：{formatRate(backend?.branch_rate)}</div>
            <div>阈值状态：{formatStatus(thresholds?.backend_ok)}</div>
          </div>
        </div>

        <div className="rounded-xl border border-border bg-card p-4 shadow-sm" data-testid="coverage-frontend">
          <h3 className="text-sm font-semibold text-foreground">前端覆盖率</h3>
          <div className="mt-3 space-y-1 text-sm text-muted-foreground">
            <div>语句覆盖率：{formatRate(frontend?.statement_rate)}</div>
            <div>函数覆盖率：{formatRate(frontend?.function_rate)}</div>
            <div>分支覆盖率：{formatRate(frontend?.branch_rate)}</div>
            <div>阈值状态：{formatStatus(thresholds?.frontend_ok)}</div>
          </div>
        </div>
      </div>

      <p className="text-xs text-muted-foreground">
        覆盖率数据来源于 `coverage.xml` 与 Vitest 覆盖率报告。请确保已执行覆盖率生成脚本。
      </p>
    </section>
  )
}
