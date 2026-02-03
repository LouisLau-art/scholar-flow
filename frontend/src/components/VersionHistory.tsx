'use client'

import { useState, useEffect } from 'react'
import { authService } from '@/services/auth'
import { Loader2, FileText, Download, MessageSquare, History, ChevronDown, ChevronUp } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { toast } from 'sonner'

interface VersionHistoryProps {
  manuscriptId: string
}

export default function VersionHistory({ manuscriptId }: VersionHistoryProps) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [expandedRevision, setExpandedRevision] = useState<string | null>(null)

  useEffect(() => {
    async function fetchData() {
      try {
        const token = await authService.getAccessToken()
        if (!token) return

        const res = await fetch(`/api/v1/manuscripts/${manuscriptId}/versions`, {
          headers: { Authorization: `Bearer ${token}` }
        })
        const result = await res.json()
        if (result.success) {
          setData(result.data)
          const versions = Array.isArray(result.data?.versions) ? result.data.versions : []
          // 默认展开最新的修回（v2+），方便 Editor 直接看到 response letter（含图片）
          const latest = versions.reduce((acc: any, cur: any) => {
            if (!acc) return cur
            if ((cur?.version_number ?? 0) > (acc?.version_number ?? 0)) return cur
            return acc
          }, null as any)
          if (latest && (latest.version_number ?? 0) > 1 && latest.id) {
            setExpandedRevision(String(latest.id))
          }
        }
      } catch (err) {
        console.error('Failed to fetch history:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [manuscriptId])

  const handleDownload = async (versionNum: number) => {
    try {
      const token = await authService.getAccessToken()
      if (!token) {
        toast.error('Please sign in again.')
        return
      }
      const res = await fetch(`/api/v1/manuscripts/${encodeURIComponent(manuscriptId)}/versions/${encodeURIComponent(String(versionNum))}/pdf-signed`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      const json = await res.json().catch(() => null)
      const signedUrl = json?.data?.signed_url
      if (!res.ok || !json?.success || !signedUrl) {
        toast.error(json?.detail || json?.message || 'Failed to generate download link')
        return
      }
      window.open(String(signedUrl), '_blank')
    } catch (e) {
      toast.error('Download error')
    }
  }

  if (loading) return <div className="py-4 flex justify-center"><Loader2 className="h-6 w-6 animate-spin text-slate-400" /></div>
  if (!data || (!data.versions?.length && !data.revisions?.length)) return null

  // Combine versions and revisions for chronological display?
  // Or just list Versions, and show linked Revision info.
  // Version 1 (Initial)
  // Revision 1 Request (Editor) -> Version 2 (Author Response)
  
  // Let's render Versions list descending.
  const versions = [...(data.versions || [])].sort((a, b) => b.version_number - a.version_number)
  const revisions = data.revisions || []

  const getRevisionForVersion = (verNum: number) => {
    // Version N (where N > 1) is a response to Revision Round N-1?
    // Round 1 request -> leads to Version 2.
    // So Version 2 is linked to Revision Round 1.
    if (verNum === 1) return null
    return revisions.find((r: any) => r.round_number === verNum - 1)
  }

  return (
    <Card className="border-slate-200 shadow-sm">
      <CardHeader className="pb-3 border-b border-slate-100">
        <CardTitle className="text-lg flex items-center gap-2">
          <History className="h-5 w-5 text-slate-500" />
          Version History
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div className="divide-y divide-slate-100">
          {versions.map((version: any) => {
            const revision = getRevisionForVersion(version.version_number)
            const isInitial = version.version_number === 1
            const isExpanded = expandedRevision === version.id

            return (
              <div key={version.id} className="p-4 hover:bg-slate-50 transition-colors">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    <div className={`h-8 w-8 rounded-full flex items-center justify-center text-sm font-bold ${
                      isInitial ? 'bg-blue-100 text-blue-700' : 'bg-indigo-100 text-indigo-700'
                    }`}>
                      v{version.version_number}
                    </div>
                    <div>
                      <p className="font-medium text-slate-900">
                        {isInitial ? 'Initial Submission' : `Revision (Round ${version.version_number - 1})`}
                      </p>
                      <p className="text-xs text-slate-500">
                        {new Date(version.created_at).toLocaleDateString()} at {new Date(version.created_at).toLocaleTimeString()}
                      </p>
                    </div>
                  </div>
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={() => handleDownload(version.version_number)}
                    className="gap-2 h-8"
                  >
                    <Download className="h-3 w-3" /> PDF
                  </Button>
                </div>

                {revision && (
                  <div className="mt-3 pl-11">
                    <button 
                      onClick={() => setExpandedRevision(isExpanded ? null : version.id)}
                      className="text-xs font-medium text-slate-500 hover:text-slate-800 flex items-center gap-1"
                    >
                      {isExpanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                      {isExpanded ? 'Hide' : 'Show'} Revision Details (Editor Request & Author Response)
                    </button>
                    
                    {isExpanded && (
                      <div className="mt-3 space-y-4 text-sm animate-in fade-in slide-in-from-top-1">
                        <div className="bg-amber-50 p-3 rounded-lg border border-amber-100">
                          <p className="font-semibold text-amber-800 mb-1 text-xs uppercase tracking-wide">Editor Request ({revision.decision_type})</p>
                          <div className="prose prose-sm max-w-none text-slate-700">
                            {revision.editor_comment}
                          </div>
                        </div>
                        
                        {revision.response_letter && (
                          <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
                            <p className="font-semibold text-slate-700 mb-1 text-xs uppercase tracking-wide">Author Response</p>
                            <div 
                              className="prose prose-sm max-w-none text-slate-600 prose-img:max-w-full prose-img:h-auto prose-img:rounded-md"
                              dangerouslySetInnerHTML={{ __html: revision.response_letter }} 
                            />
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
