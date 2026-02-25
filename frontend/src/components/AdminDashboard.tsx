'use client'

import Link from 'next/link'
import { Users, Settings, Shield, Library } from 'lucide-react'

export default function AdminDashboard() {
  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-foreground">Admin Control Panel</h2>
        <p className="mt-1 text-muted-foreground">System-wide settings and user management.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* User Management Card */}
        <Link href="/admin/users" className="group block">
          <div className="rounded-2xl border border-border bg-card p-6 shadow-sm transition-all hover:border-primary hover:shadow-md">
            <div className="flex items-center gap-4 mb-4">
              <div className="rounded-xl bg-primary/10 p-3 text-primary transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
                <Users className="h-6 w-6" />
              </div>
              <h3 className="text-lg font-bold text-foreground">User Management</h3>
            </div>
            <p className="text-sm text-muted-foreground">
              View directory, manage roles (Editor/Reviewer), and invite new internal members.
            </p>
          </div>
        </Link>

        {/* Placeholder for System Settings */}
        <Link href="/admin/journals" className="group block">
          <div className="rounded-2xl border border-border bg-card p-6 shadow-sm transition-all hover:border-primary hover:shadow-md">
            <div className="flex items-center gap-4 mb-4">
              <div className="rounded-xl bg-primary/10 p-3 text-primary transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
                <Library className="h-6 w-6" />
              </div>
              <h3 className="text-lg font-bold text-foreground">Journal Management</h3>
            </div>
            <p className="text-sm text-muted-foreground">
              Create and maintain journals used by submission workflow and editorial routing.
            </p>
          </div>
        </Link>

        {/* Placeholder for System Settings */}
        <div className="cursor-not-allowed rounded-2xl border border-border bg-card p-6 opacity-60 shadow-sm">
          <div className="flex items-center gap-4 mb-4">
            <div className="rounded-xl bg-muted p-3 text-muted-foreground">
              <Settings className="h-6 w-6" />
            </div>
            <h3 className="text-lg font-bold text-foreground">System Settings</h3>
          </div>
          <p className="text-sm text-muted-foreground">
            Global configuration, email templates, and integrations. (Coming Soon)
          </p>
        </div>

        {/* Placeholder for Security Audit */}
        <div className="cursor-not-allowed rounded-2xl border border-border bg-card p-6 opacity-60 shadow-sm">
          <div className="flex items-center gap-4 mb-4">
            <div className="rounded-xl bg-muted p-3 text-muted-foreground">
              <Shield className="h-6 w-6" />
            </div>
            <h3 className="text-lg font-bold text-foreground">Security Audit</h3>
          </div>
          <p className="text-sm text-muted-foreground">
            View access logs, role changes, and security alerts. (Coming Soon)
          </p>
        </div>
      </div>
    </div>
  )
}
