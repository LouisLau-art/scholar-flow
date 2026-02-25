export default function Loading() {
  return (
    <div className="min-h-screen bg-muted/40">
      <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8 space-y-6 animate-pulse">
        <div className="h-24 rounded-xl bg-card border border-border" />
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          <div className="lg:col-span-8 space-y-6">
            <div className="h-[520px] rounded-xl bg-card border border-border" />
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
              <div className="h-56 rounded-xl bg-card border border-border" />
              <div className="h-56 rounded-xl bg-card border border-border" />
              <div className="h-56 rounded-xl bg-card border border-border" />
            </div>
            <div className="h-64 rounded-xl bg-card border border-border" />
          </div>
          <div className="lg:col-span-4 space-y-6">
            <div className="h-32 rounded-xl bg-card border border-border" />
            <div className="h-40 rounded-xl bg-card border border-border" />
            <div className="h-56 rounded-xl bg-card border border-border" />
          </div>
        </div>
        <div className="h-56 rounded-xl bg-card border border-border" />
      </div>
    </div>
  )
}
