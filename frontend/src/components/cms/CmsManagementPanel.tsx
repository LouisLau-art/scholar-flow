'use client'

import { useState } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import CmsPagesPanel from '@/components/cms/CmsPagesPanel'
import CmsMenuPanel from '@/components/cms/CmsMenuPanel'
import type { CmsPage } from '@/services/cms'

export default function CmsManagementPanel() {
  const [pages, setPages] = useState<CmsPage[]>([])

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-slate-200 bg-white p-6">
        <h2 className="text-xl font-bold text-slate-900">Website Management</h2>
        <p className="mt-2 text-slate-600 text-sm">
          Create pages, publish content, and manage global navigation menus.
        </p>
      </div>

      <Tabs defaultValue="pages" className="space-y-6">
        <TabsList className="border border-border bg-background p-1">
          <TabsTrigger value="pages">Pages</TabsTrigger>
          <TabsTrigger value="menu">Menu</TabsTrigger>
        </TabsList>

        <TabsContent value="pages">
          <CmsPagesPanel onPagesLoaded={setPages} />
        </TabsContent>
        <TabsContent value="menu">
          <CmsMenuPanel pages={pages} />
        </TabsContent>
      </Tabs>
    </div>
  )
}

