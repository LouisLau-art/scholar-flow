# Quickstart: Align Manuscript Detail Page Layout

## Component Structure

```tsx
// app/(admin)/editor/manuscript/[id]/page.tsx
export default function ManuscriptPage() {
  return (
    <div className="space-y-6">
      <ManuscriptHeader manuscript={data} />
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <FileSectionCard title="Cover Letter" files={...} />
        <FileSectionCard title="Original Manuscript" files={...} />
        <FileSectionCard 
          title="Peer Review Files" 
          files={...} 
          action={<UploadReviewFileButton />} 
        />
      </div>

      <InvoiceInfoPanel invoice={data.invoice} />
    </div>
  )
}
```

## Tailwind Grid for Header
```tsx
<div className="grid grid-cols-12 gap-4">
  <div className="col-span-12 md:col-span-8">
    <h1>{title}</h1>
    <AuthorsList list={authors} />
  </div>
  <div className="col-span-12 md:col-span-4 bg-muted p-4 rounded">
    <Label>Internal Owner</Label>
    <div>{ownerName}</div>
    <Label>Assigned Editor</Label>
    <div>{editorName}</div>
  </div>
</div>
```
