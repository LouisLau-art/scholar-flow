'use client'

import { useCallback, useEffect, useState } from 'react'
import { doiApi, DOITask } from '@/lib/api/doi'
import { DOITaskList } from '@/components/doi/DOITaskList'
import { Button } from '@/components/ui/button'
import { RefreshCw } from 'lucide-react'
import SiteHeader from '@/components/layout/SiteHeader'

export default function DOITasksPage() {
  const [tasks, setTasks] = useState<DOITask[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<'all' | 'failed'>('all')

  const loadTasks = useCallback(async () => {
    setLoading(true)
    try {
      const res = filter === 'failed' 
        ? await doiApi.getFailedTasks()
        : await doiApi.getTasks()
      setTasks(res.items)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [filter])

  useEffect(() => {
    void loadTasks()
  }, [loadTasks])

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <SiteHeader />
      <main className="flex-1 w-full max-w-7xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">DOI Tasks</h1>
            <p className="text-slate-500">Monitor and manage DOI registration tasks</p>
          </div>
          <div className="flex gap-2">
            <Button 
              variant={filter === 'all' ? 'default' : 'outline'}
              onClick={() => setFilter('all')}
            >
              All Tasks
            </Button>
            <Button 
              variant={filter === 'failed' ? 'destructive' : 'outline'}
              onClick={() => setFilter('failed')}
            >
              Failed Tasks
            </Button>
            <Button
              variant="outline"
              size="icon"
              onClick={loadTasks}
              aria-label="Refresh DOI tasks"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>

        <DOITaskList tasks={tasks} onRefresh={loadTasks} />
      </main>
    </div>
  )
}
