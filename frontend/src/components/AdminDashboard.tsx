'use client'

import Link from 'next/link'
import { Users, Settings, Shield, Library } from 'lucide-react'

export default function AdminDashboard() {
  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-slate-900">Admin Control Panel</h2>
        <p className="mt-1 text-slate-500">System-wide settings and user management.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* User Management Card */}
        <Link href="/admin/users" className="group block">
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 hover:border-blue-500 hover:shadow-md transition-all">
            <div className="flex items-center gap-4 mb-4">
              <div className="p-3 bg-blue-50 text-blue-600 rounded-xl group-hover:bg-blue-600 group-hover:text-white transition-colors">
                <Users className="h-6 w-6" />
              </div>
              <h3 className="text-lg font-bold text-slate-900">User Management</h3>
            </div>
            <p className="text-slate-500 text-sm">
              View directory, manage roles (Editor/Reviewer), and invite new internal members.
            </p>
          </div>
        </Link>

        {/* Placeholder for System Settings */}
        <Link href="/admin/journals" className="group block">
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 hover:border-blue-500 hover:shadow-md transition-all">
            <div className="flex items-center gap-4 mb-4">
              <div className="p-3 bg-blue-50 text-blue-600 rounded-xl group-hover:bg-blue-600 group-hover:text-white transition-colors">
                <Library className="h-6 w-6" />
              </div>
              <h3 className="text-lg font-bold text-slate-900">Journal Management</h3>
            </div>
            <p className="text-slate-500 text-sm">
              Create and maintain journals used by submission workflow and editorial routing.
            </p>
          </div>
        </Link>

        {/* Placeholder for System Settings */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 opacity-60 cursor-not-allowed">
          <div className="flex items-center gap-4 mb-4">
            <div className="p-3 bg-slate-100 text-slate-500 rounded-xl">
              <Settings className="h-6 w-6" />
            </div>
            <h3 className="text-lg font-bold text-slate-900">System Settings</h3>
          </div>
          <p className="text-slate-500 text-sm">
            Global configuration, email templates, and integrations. (Coming Soon)
          </p>
        </div>

        {/* Placeholder for Security Audit */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 opacity-60 cursor-not-allowed">
          <div className="flex items-center gap-4 mb-4">
            <div className="p-3 bg-slate-100 text-slate-500 rounded-xl">
              <Shield className="h-6 w-6" />
            </div>
            <h3 className="text-lg font-bold text-slate-900">Security Audit</h3>
          </div>
          <p className="text-slate-500 text-sm">
            View access logs, role changes, and security alerts. (Coming Soon)
          </p>
        </div>
      </div>
    </div>
  )
}
