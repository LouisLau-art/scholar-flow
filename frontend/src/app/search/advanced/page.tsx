import Link from 'next/link'

import SiteHeader from '@/components/layout/SiteHeader'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

export default function AdvancedSearchPage() {
  return (
    <div className="min-h-screen bg-muted/40 flex flex-col">
      <SiteHeader />

      <main className="flex-1 mx-auto w-full max-w-5xl px-4 py-12">
        <header className="mb-8">
          <h1 className="text-3xl font-serif font-bold text-foreground">Advanced Search</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            按标题、DOI、期刊、作者与年份区间组合检索。提交后将跳转到统一搜索结果页。
          </p>
        </header>

        <form action="/search" method="get" className="rounded-2xl border border-border bg-card p-6 shadow-sm space-y-6">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="mode">Mode</Label>
              <select
                id="mode"
                name="mode"
                className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                defaultValue="articles"
              >
                <option value="articles">Articles</option>
                <option value="journals">Journals</option>
              </select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="q">Keyword</Label>
              <Input id="q" name="q" placeholder="Any keyword" />
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="title">Title</Label>
              <Input id="title" name="title" placeholder="Article title" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="doi">DOI</Label>
              <Input id="doi" name="doi" placeholder="10.xxxx/..." />
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="journal">Journal</Label>
              <Input id="journal" name="journal" placeholder="Journal title or slug" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="author">Author</Label>
              <Input id="author" name="author" placeholder="Author name" />
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="year_from">Year From</Label>
              <Input id="year_from" name="year_from" inputMode="numeric" pattern="[0-9]*" placeholder="2020" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="year_to">Year To</Label>
              <Input id="year_to" name="year_to" inputMode="numeric" pattern="[0-9]*" placeholder="2026" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="sort">Sort</Label>
              <select
                id="sort"
                name="sort"
                className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                defaultValue="latest"
              >
                <option value="latest">Latest</option>
                <option value="oldest">Oldest</option>
                <option value="relevance">Relevance</option>
                <option value="title_asc">Title A-Z</option>
                <option value="title_desc">Title Z-A</option>
              </select>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3 pt-2">
            <Button type="submit">Search</Button>
            <Link href="/search" className="text-sm text-muted-foreground underline-offset-4 hover:underline">
              Back to Search
            </Link>
          </div>
        </form>
      </main>
    </div>
  )
}
