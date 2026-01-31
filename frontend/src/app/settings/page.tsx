"use client"

import SiteHeader from "@/components/layout/SiteHeader"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ProfileForm } from "@/components/settings/ProfileForm"
import { AcademicForm } from "@/components/settings/AcademicForm"
import { AvatarUpload } from "@/components/settings/AvatarUpload"
import { PasswordChangeForm } from "@/components/settings/PasswordChangeForm"
import { useProfile } from "@/hooks/useProfile"
import { Loader2, User, BookOpen, Shield } from "lucide-react"

export default function SettingsPage() {
  const { profile, isLoading, saveProfile, isSaving, changePassword } = useProfile()

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex flex-col">
        <SiteHeader />
        <main className="flex-1 flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </main>
      </div>
    )
  }

  if (!profile) return null

  return (
    <div className="min-h-screen bg-background flex flex-col font-sans">
      <SiteHeader />

      <main className="flex-1 mx-auto max-w-4xl w-full px-4 py-12 sm:px-6">
        <div className="mb-8">
          <h1 className="text-3xl font-serif font-bold text-foreground tracking-tight">Account Settings</h1>
          <p className="mt-1 text-muted-foreground font-medium">Manage your profile, academic details, and security.</p>
        </div>

        <Tabs defaultValue="profile" className="space-y-8">
          <TabsList className="bg-muted p-1 rounded-xl shadow-sm border border-border w-full sm:w-auto grid grid-cols-3 sm:flex">
            <TabsTrigger value="profile" className="flex items-center gap-2 rounded-lg px-4 py-2 data-[state=active]:bg-background data-[state=active]:text-foreground shadow-sm">
              <User className="h-4 w-4" /> <span className="hidden sm:inline">Profile</span>
            </TabsTrigger>
            <TabsTrigger value="academic" className="flex items-center gap-2 rounded-lg px-4 py-2 data-[state=active]:bg-background data-[state=active]:text-foreground shadow-sm">
              <BookOpen className="h-4 w-4" /> <span className="hidden sm:inline">Academic</span>
            </TabsTrigger>
            <TabsTrigger value="security" className="flex items-center gap-2 rounded-lg px-4 py-2 data-[state=active]:bg-background data-[state=active]:text-foreground shadow-sm">
              <Shield className="h-4 w-4" /> <span className="hidden sm:inline">Security</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="profile" className="bg-card p-6 sm:p-8 rounded-2xl shadow-sm border border-border text-card-foreground">
            <div className="max-w-xl space-y-8">
              <div>
                <h2 className="text-xl font-bold text-foreground mb-6">Profile Picture</h2>
                <AvatarUpload 
                  userId={profile.id}
                  currentAvatarUrl={profile.avatar_url}
                  userName={profile.full_name || profile.email}
                  onUploadSuccess={(url) => saveProfile({ avatar_url: url })}
                />
              </div>
              
              <div className="pt-8 border-t border-border">
                <h2 className="text-xl font-bold text-foreground mb-6">Basic Information</h2>
                <ProfileForm user={profile} onSave={saveProfile} isSaving={isSaving} />
              </div>
            </div>
          </TabsContent>

          <TabsContent value="academic" className="bg-card p-6 sm:p-8 rounded-2xl shadow-sm border border-border text-card-foreground">
            <div className="max-w-xl">
              <h2 className="text-xl font-bold text-foreground mb-6">Academic Background</h2>
              <AcademicForm user={profile} onSave={saveProfile} isSaving={isSaving} />
            </div>
          </TabsContent>

          <TabsContent value="security" className="bg-card p-6 sm:p-8 rounded-2xl shadow-sm border border-border text-card-foreground">
            <div className="max-w-xl">
              <h2 className="text-xl font-bold text-foreground mb-6">Security Settings</h2>
              <p className="text-muted-foreground text-sm mb-6">Manage your password and account security.</p>
              <PasswordChangeForm onSave={(password) => changePassword(password)} />
            </div>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  )
}
