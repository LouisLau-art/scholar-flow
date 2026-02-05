export type ManuscriptFile = {
  id: string
  file_type: 'cover_letter' | 'manuscript' | 'review_attachment' | string
  label?: string | null
  bucket?: string | null
  path?: string | null
  signed_url?: string | null
  created_at?: string | null
}

export function filterFilesByType(files: ManuscriptFile[] | undefined | null, type: string): ManuscriptFile[] {
  const list = Array.isArray(files) ? files : []
  const t = String(type || '').toLowerCase()
  return list.filter((f) => String(f?.file_type || '').toLowerCase() === t)
}

