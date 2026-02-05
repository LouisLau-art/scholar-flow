'use client'

import { useEffect, useState } from 'react'
import { EditorApi } from '@/services/editorApi'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { format } from 'date-fns'
import { Activity } from 'lucide-react'

interface AuditLog {
  id: string
  from_status: string
  to_status: string
  comment: string | null
  created_at: string
  user?: {
    full_name?: string
    email?: string
  }
}

interface AuditLogTimelineProps {
  manuscriptId: string
}

export function AuditLogTimeline({ manuscriptId }: AuditLogTimelineProps) {
  const [logs, setLogs] = useState<AuditLog[]>([])

  useEffect(() => {
    EditorApi.getAuditLogs(manuscriptId).then((res) => {
      if (res.success) setLogs(res.data)
    })
  }, [manuscriptId])

  return (
    <Card className="shadow-sm">
      <CardHeader className="py-4 border-b">
        <CardTitle className="text-sm font-bold uppercase tracking-wide flex items-center gap-2 text-slate-700">
          <Activity className="h-4 w-4" />
          Status History
        </CardTitle>
      </CardHeader>
      <CardContent className="p-5">
        <div className="relative pl-4 border-l-2 border-slate-100 space-y-6">
          {logs.map((log, idx) => (
            <div key={log.id} className={`relative ${idx > 0 ? 'opacity-80' : ''}`}>
              <div
                className={`absolute -left-[21px] top-1 w-3 h-3 rounded-full border-2 border-white ${
                  idx === 0 ? 'bg-blue-500' : 'bg-slate-300'
                }`}
              ></div>
              <div className="text-sm font-medium text-slate-900 capitalize">
                {log.to_status?.replace('_', ' ') || 'Unknown'}
              </div>
              <div className="text-xs text-slate-500">
                {format(new Date(log.created_at), 'yyyy-MM-dd HH:mm')} by{' '}
                {log.user?.full_name || log.user?.email || 'System'}
              </div>
              {log.comment && (
                <div className="text-xs text-slate-600 mt-1 bg-slate-50 p-2 rounded border border-slate-100 italic">
                  &ldquo;{log.comment}&rdquo;
                </div>
              )}
            </div>
          ))}
          {logs.length === 0 && <div className="text-xs text-slate-400">No history available.</div>}
        </div>
      </CardContent>
    </Card>
  )
}
