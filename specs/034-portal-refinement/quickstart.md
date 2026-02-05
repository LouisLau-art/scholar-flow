# Quickstart: Refine Portal Home and Navigation

## Component Architecture

```tsx
// frontend/src/components/portal/HomeBanner.tsx
export function HomeBanner() {
  return (
    <section className="bg-slate-900 text-white py-20 px-4">
      <div className="max-w-6xl mx-auto flex flex-col items-center text-center">
        <h1 className="text-4xl md:text-6xl font-serif mb-6">{siteConfig.title}</h1>
        <p className="text-xl text-slate-300 max-w-2xl mb-8">{siteConfig.description}</p>
        <div className="flex gap-4 mb-10">
           <Badge variant="outline">ISSN: {siteConfig.issn}</Badge>
           <Badge variant="secondary">Impact Factor: {siteConfig.impact_factor}</Badge>
        </div>
        <Button size="lg" asChild>
          <Link href="/submit">Submit Manuscript</Link>
        </Button>
      </div>
    </section>
  )
}
```

## Public API Client
```ts
// frontend/src/services/portal.ts
export async function getLatestArticles() {
  const response = await fetch('/api/v1/articles/latest');
  if (!response.ok) throw new Error('Failed to fetch articles');
  return response.json();
}
```
