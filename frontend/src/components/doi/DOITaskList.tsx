'use client'

import { DOITask } from '@/lib/api/doi'
import { DOIStatus } from './DOIStatus'
import { Button } from '@/components/ui/button'
import { RefreshCw } from 'lucide-react'
import { useState } from 'react'

interface DOITaskListProps {
  tasks: DOITask[]
  onRefresh?: () => void
}

export function DOITaskList({ tasks, onRefresh }: DOITaskListProps) {
  return (
    <div className="rounded-md border border-border bg-card overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-muted text-muted-foreground border-b border-border">
          <tr>
            <th className="h-10 px-4 text-left font-semibold uppercase text-[10px] tracking-wider">Task ID</th>
            <th className="h-10 px-4 text-left font-semibold uppercase text-[10px] tracking-wider">Type</th>
            <th className="h-10 px-4 text-left font-semibold uppercase text-[10px] tracking-wider">Status</th>
            <th className="h-10 px-4 text-left font-semibold uppercase text-[10px] tracking-wider">Attempts</th>
            <th className="h-10 px-4 text-left font-semibold uppercase text-[10px] tracking-wider">Run At</th>
            <th className="h-10 px-4 text-left font-semibold uppercase text-[10px] tracking-wider">Error</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {tasks.map((task) => (
            <tr key={task.id} className="hover:bg-muted/50 transition-colors">
              <td className="p-4 font-mono text-xs text-foreground">{task.id.slice(0, 8)}...</td>
              <td className="p-4 capitalize text-foreground">{task.task_type}</td>
              <td className="p-4">
                <DOIStatus status={task.status} />
              </td>
              <td className="p-4 text-muted-foreground">{task.attempts}/{task.max_attempts}</td>
              <td className="p-4 text-muted-foreground">
                {new Date(task.run_at).toLocaleString()}
              </td>
              <td className="p-4 max-w-[200px] truncate text-destructive font-medium" title={task.last_error}>
                {task.last_error || '-'}
              </td>
            </tr>
          ))}
          {tasks.length === 0 && (
            <tr>
              <td colSpan={6} className="p-12 text-center text-muted-foreground italic">
                No DOI registration tasks found.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
