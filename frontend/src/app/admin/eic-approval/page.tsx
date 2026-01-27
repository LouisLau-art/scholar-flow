'use client'

import { useState } from 'react'
import { ShieldCheck, Globe } from 'lucide-react'

export default function EICApprovalPage() {
  const [pendingItems, setPendingItems] = useState([
    { id: 'm-001', title: 'Advances in Quantum Computing', financeConfirmed: true }
  ])

  const handlePublish = (id: string) => {
    console.log('Publishing manuscript', id)
    setPendingItems(pendingItems.filter(item => item.id !== id))
  }

  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <div className="mx-auto max-w-4xl">
        <header className="mb-12">
          <h1 className="font-serif text-4xl font-bold text-slate-900">Editor-in-Chief Approval</h1>
          <p className="mt-2 text-slate-600 text-lg font-medium">Final authority gate before publication.</p>
        </header>

        <div className="space-y-6">
          {pendingItems.map(item => (
            <div key={item.id} className="bg-white p-8 rounded-xl shadow-sm ring-1 ring-slate-200 flex items-center justify-between">
              <div className="flex gap-6 items-center">
                <div className="bg-blue-50 p-4 rounded-full">
                  <ShieldCheck className="h-8 w-8 text-blue-600" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-slate-900">{item.title}</h3>
                  <div className="mt-2 flex items-center gap-4">
                    <span className="text-xs font-bold text-green-600 bg-green-50 px-2 py-1 rounded">PAYMENT CONFIRMED</span>
                    <span className="text-xs text-slate-400">ID: {item.id}</span>
                  </div>
                </div>
              </div>

              <button 
                onClick={() => handlePublish(item.id)}
                className="flex items-center gap-2 bg-slate-900 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700 transition-all shadow-lg hover:shadow-blue-500/20"
              >
                <Globe className="h-5 w-5" /> GO LIVE
              </button>
            </div>
          ))}

          {pendingItems.length === 0 && (
            <div className="flex flex-col items-center justify-center py-24 bg-white rounded-xl border border-slate-200 shadow-sm">
              <div className="rounded-full bg-green-50 p-6 mb-6">
                <ShieldCheck className="h-16 w-16 text-green-600" />
              </div>
              <h2 className="text-2xl font-bold text-slate-900">All Systems Go!</h2>
              <p className="mt-2 text-slate-500">No pending manuscripts for final approval.</p>
              <button 
                onClick={() => window.location.reload()} 
                className="mt-8 text-sm text-blue-600 hover:text-blue-800 font-medium"
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