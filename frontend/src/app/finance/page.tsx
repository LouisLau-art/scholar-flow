'use client'

import { useState } from 'react'
import { DollarSign, CheckCircle, RotateCcw, FileText } from 'lucide-react'

export default function FinanceDashboard() {
  /**
   * 财务管理后台
   * 遵循章程：slate-900 风格，原子化组件
   * 落实 Spec：支持确认到账与撤销回滚 (Edge Cases)
   */
  const [invoices, setInvoices] = useState([
    { id: 'inv-001', title: 'Deep Learning in Medicine', amount: 1500, status: 'unpaid' }
  ])

  const handleConfirm = (id: string) => {
    setInvoices(invoices.map(inv => inv.id === id ? { ...inv, status: 'paid' } : inv))
    console.log('Payment confirmed for', id)
  }

  const handleRollback = (id: string) => {
    // 落实 Spec: 财务误操作回滚
    setInvoices(invoices.map(inv => inv.id === id ? { ...inv, status: 'unpaid' } : inv))
    console.log('Payment rolled back for', id)
  }

  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <div className="mx-auto max-w-5xl">
        <header className="mb-10">
          <h1 className="font-serif text-3xl font-bold text-slate-900 flex items-center gap-3">
            <DollarSign className="h-8 w-8 text-blue-600" /> Financial Overview
          </h1>
        </header>

        <div className="bg-white rounded-lg shadow-sm ring-1 ring-slate-200 overflow-hidden">
          <table className="w-full text-left">
            <thead className="bg-slate-900 text-white">
              <tr>
                <th className="px-6 py-4 font-semibold text-sm">Manuscript</th>
                <th className="px-6 py-4 font-semibold text-sm">Amount</th>
                <th className="px-6 py-4 font-semibold text-sm">Status</th>
                <th className="px-6 py-4 font-semibold text-sm text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {invoices.map((inv) => (
                <tr key={inv.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-6 py-4 font-medium text-slate-900">{inv.title}</td>
                  <td className="px-6 py-4 text-slate-600">${inv.amount}</td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex px-2 py-1 rounded text-xs font-bold ${
                      inv.status === 'paid' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
                    }`}>
                      {inv.status.toUpperCase()}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right flex justify-end gap-2">
                    {inv.status === 'unpaid' ? (
                      <button 
                        onClick={() => handleConfirm(inv.id)} 
                        className="flex items-center gap-1 px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700 transition-colors text-xs"
                      >
                        <CheckCircle className="h-4 w-4" /> Confirm Payment
                      </button>
                    ) : (
                      <button 
                        onClick={() => handleRollback(inv.id)} 
                        className="flex items-center gap-1 px-3 py-1 bg-slate-200 text-slate-700 rounded hover:bg-slate-300 transition-colors text-xs"
                      >
                        <RotateCcw className="h-4 w-4" /> Rollback
                      </button>
                    )}
                    <button 
                      onClick={() => alert("Invoice PDF is being generated...")}
                      className="flex items-center gap-1 px-3 py-1 border border-slate-300 text-slate-600 rounded hover:bg-slate-50 transition-colors text-xs"
                    >
                      <FileText className="h-4 w-4" /> View Invoice
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
