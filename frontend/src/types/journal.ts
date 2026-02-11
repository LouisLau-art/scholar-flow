export type Journal = {
  id: string
  title: string
  slug: string
  description?: string | null
  issn?: string | null
  impact_factor?: number | null
  cover_url?: string | null
  is_active?: boolean
  created_at?: string
  updated_at?: string | null
}

export type JournalCreatePayload = {
  title: string
  slug: string
  description?: string | null
  issn?: string | null
  impact_factor?: number | null
  cover_url?: string | null
  is_active?: boolean
}

export type JournalUpdatePayload = Partial<JournalCreatePayload>
