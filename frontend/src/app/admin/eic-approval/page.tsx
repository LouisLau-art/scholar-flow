'use client'

import { useState } from 'react'
import { ShieldCheck, Globe } from 'lucide-react'
import SiteHeader from '@/components/layout/SiteHeader'

export default function EICApprovalPage() {
  const [pendingItems, setPendingItems] = useState([
    { id: 'm-001', title: 'Advances in Quantum Computing', financeConfirmed: true }
  ])

  const handlePublish = (id: string) => {
    setPendingItems(pendingItems.filter(item => item.id !== id))
  }

  return (
    <div className="min-h-screen bg-muted/40">
      <SiteHeader />
      <div className="mx-auto max-w-4xl p-8">
        <header className="mb-12">
          <h1 className="font-serif text-4xl font-bold text-foreground">Editor-in-Chief Approval</h1>
          <p className="mt-2 text-muted-foreground text-lg font-medium">Final authority gate before publication.</p>
        </header>

        <div className="space-y-6">
          {pendingItems.map(item => (
            <div key={item.id} className="bg-card p-8 rounded-xl shadow-sm ring-1 ring-border flex items-center justify-between">
              <div className="flex gap-6 items-center">
                <div className="bg-primary/10 p-4 rounded-full">
                  <ShieldCheck className="h-8 w-8 text-primary" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-foreground">{item.title}</h3>
                  <div className="mt-2 flex items-center gap-4">
                    <span className="text-xs font-bold text-green-600 bg-green-50 px-2 py-1 rounded">PAYMENT CONFIRMED</span>
                    <span className="text-xs text-muted-foreground">ID: {item.id}</span>
                  </div>
                </div>
              </div>

              <button 
                onClick={() => handlePublish(item.id)}
                className="flex items-center gap-2 bg-primary text-primary-foreground px-6 py-3 rounded-lg font-semibold hover:bg-primary/90 transition-all shadow-lg hover:shadow-primary/20"
              >
                <Globe className="h-5 w-5" /> GO LIVE
              </button>
            </div>
          ))}

          {pendingItems.length === 0 && (
            <div className="flex flex-col items-center justify-center py-24 bg-card rounded-xl border border-border shadow-sm">
              <div className="rounded-full bg-green-50 p-6 mb-6">
                <ShieldCheck className="h-16 w-16 text-green-600" />
              </div>
              <h2 className="text-2xl font-bold text-foreground">All Systems Go!</h2>
              <p className="mt-2 text-muted-foreground">No pending manuscripts for final approval.</p>
              <button 
                onClick={() => window.location.reload()} 
                className="mt-8 text-sm text-primary hover:text-primary/80 font-medium"
              >
                Refresh Dashboard
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
