import type { Journal } from '@/types/journal'

export const STORAGE_UPLOAD_TIMEOUT_MS = 90_000
export const SUPPLEMENTAL_UPLOAD_TIMEOUT_MS = 60_000
export const METADATA_PARSE_TIMEOUT_MS = 25_000
export const METADATA_PARSE_TOTAL_TIMEOUT_MS = 35_000
const DIRECT_API_ORIGIN = (process.env.NEXT_PUBLIC_API_URL || '').trim().replace(/\/$/, '')

export type MetadataState = {
  title: string
  abstract: string
  submissionEmail: string
  authorContacts: SubmissionAuthorContact[]
}

export type SubmissionAuthorContact = {
  id: string
  name: string
  email: string
  affiliation: string
  city: string
  countryOrRegion: string
  isCorresponding: boolean
}

export type TouchedState = {
  title: boolean
  abstract: boolean
  submissionEmail: boolean
  authorContacts: boolean
  datasetUrl: boolean
  sourceCodeUrl: boolean
  journal: boolean
  policyConsent: boolean
  ethicsConsent: boolean
}

export type MetadataParsePayload = {
  response: Response
  raw: string
  result: any
  traceId: string
}

export const INITIAL_METADATA: MetadataState = {
  title: '',
  abstract: '',
  submissionEmail: '',
  authorContacts: [createAuthorContact({ isCorresponding: true })],
}

export const INITIAL_TOUCHED: TouchedState = {
  title: false,
  abstract: false,
  submissionEmail: false,
  authorContacts: false,
  datasetUrl: false,
  sourceCodeUrl: false,
  journal: false,
  policyConsent: false,
  ethicsConsent: false,
}

const SIMPLE_EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export function createAuthorContact(overrides: Partial<Omit<SubmissionAuthorContact, 'id'>> = {}): SubmissionAuthorContact {
  return {
    id: `author-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`,
    name: '',
    email: '',
    affiliation: '',
    city: '',
    countryOrRegion: '',
    isCorresponding: false,
    ...overrides,
  }
}

export function isValidEmail(value: string): boolean {
  const trimmed = value.trim()
  return SIMPLE_EMAIL_PATTERN.test(trimmed)
}

export function isAuthorContactComplete(author: SubmissionAuthorContact): boolean {
  return (
    author.name.trim().length > 0 &&
    author.email.trim().length > 0 &&
    author.affiliation.trim().length > 0 &&
    author.city.trim().length > 0 &&
    author.countryOrRegion.trim().length > 0 &&
    isValidEmail(author.email)
  )
}

export function hasAtLeastOneCorrespondingAuthor(authorContacts: SubmissionAuthorContact[]): boolean {
  return authorContacts.some((author) => author.isCorresponding)
}

export function hasValidAuthorContacts(authorContacts: SubmissionAuthorContact[]): boolean {
  return authorContacts.length > 0 && hasAtLeastOneCorrespondingAuthor(authorContacts) && authorContacts.every(isAuthorContactComplete)
}

export function buildAuthorContactsFromNames(names: string[]): SubmissionAuthorContact[] {
  const cleaned = names.map((item) => item.trim()).filter(Boolean).slice(0, 20)
  if (cleaned.length === 0) {
    return [createAuthorContact({ isCorresponding: true })]
  }
  return cleaned.map((name, index) =>
    createAuthorContact({
      name,
      isCorresponding: index === 0,
    }),
  )
}

export function buildAuthorContactsFromStructuredContacts(
  contacts: Array<{
    name?: unknown
    email?: unknown
    affiliation?: unknown
    city?: unknown
    country_or_region?: unknown
    is_corresponding?: unknown
  }>,
): SubmissionAuthorContact[] {
  const normalized = contacts
    .map((item) => ({
      name: String(item?.name || '').trim(),
      email: String(item?.email || '').trim().toLowerCase(),
      affiliation: String(item?.affiliation || '').trim(),
      city: String(item?.city || '').trim(),
      countryOrRegion: String(item?.country_or_region || '').trim(),
      isCorresponding: Boolean(item?.is_corresponding),
    }))
    .filter((item) => item.name || item.email || item.affiliation || item.city || item.countryOrRegion)
    .slice(0, 20)

  if (normalized.length === 0) {
    return [createAuthorContact({ isCorresponding: true })]
  }

  const hasCorresponding = normalized.some((item) => item.isCorresponding)
  return normalized.map((item, index) =>
    createAuthorContact({
      name: item.name,
      email: item.email,
      affiliation: item.affiliation,
      city: item.city,
      countryOrRegion: item.countryOrRegion,
      isCorresponding: hasCorresponding ? item.isCorresponding : index === 0,
    }),
  )
}

export function normalizeAuthorContactsForPayload(authorContacts: SubmissionAuthorContact[]) {
  return authorContacts.map((author) => ({
    name: author.name.trim(),
    email: author.email.trim(),
    affiliation: author.affiliation.trim(),
    city: author.city.trim(),
    country_or_region: author.countryOrRegion.trim(),
    is_corresponding: author.isCorresponding,
  }))
}

export function moveAuthorContact(
  authorContacts: SubmissionAuthorContact[],
  authorId: string,
  direction: 'up' | 'down',
): SubmissionAuthorContact[] {
  const currentIndex = authorContacts.findIndex((author) => author.id === authorId)
  if (currentIndex < 0) return authorContacts
  const targetIndex = direction === 'up' ? currentIndex - 1 : currentIndex + 1
  if (targetIndex < 0 || targetIndex >= authorContacts.length) return authorContacts

  const next = [...authorContacts]
  const [current] = next.splice(currentIndex, 1)
  next.splice(targetIndex, 0, current)
  return next
}

export function withTimeout<T>(promise: Promise<T>, ms: number, label: string): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const timer = window.setTimeout(() => {
      reject(new Error(`${label} timeout after ${Math.round(ms / 1000)}s`))
    }, ms)

    promise.then(
      (value) => {
        window.clearTimeout(timer)
        resolve(value)
      },
      (error) => {
        window.clearTimeout(timer)
        reject(error)
      },
    )
  })
}

function getUploadParseEndpoints(): string[] {
  const candidates = [
    DIRECT_API_ORIGIN ? `${DIRECT_API_ORIGIN}/api/v1/manuscripts/upload` : '',
    '/api/v1/manuscripts/upload',
  ].filter(Boolean)
  return Array.from(new Set(candidates))
}

function isAbortLikeError(error: unknown): boolean {
  if (error instanceof DOMException && error.name === 'AbortError') return true
  const text = String((error as any)?.name || '') + ' ' + String((error as any)?.message || '')
  return /abort/i.test(text)
}

export function isSupportedWordDocument(file: File): boolean {
  const name = String(file.name || '').toLowerCase()
  return name.endsWith('.doc') || name.endsWith('.docx')
}

export function isSupportedCoverLetterDocument(file: File): boolean {
  const name = String(file.name || '').toLowerCase()
  return name.endsWith('.pdf') || name.endsWith('.doc') || name.endsWith('.docx')
}

export function sanitizeFilename(name: string): string {
  return name.replace(/[^a-zA-Z0-9._-]/g, '_')
}

export async function parseManuscriptMetadataWithFallback(file: File): Promise<MetadataParsePayload> {
  let response: Response | null = null
  let raw = ''
  let result: any = null
  let lastError: Error | null = null
  let traceId = ''

  const parseEndpoints = getUploadParseEndpoints()
  const parseStartedAt = Date.now()
  for (let idx = 0; idx < parseEndpoints.length; idx += 1) {
    if (Date.now() - parseStartedAt > METADATA_PARSE_TOTAL_TIMEOUT_MS) {
      lastError = new Error(`Metadata parsing timeout after ${Math.round(METADATA_PARSE_TOTAL_TIMEOUT_MS / 1000)}s`)
      break
    }

    const endpoint = parseEndpoints[idx]
    const controller = new AbortController()
    const timer = window.setTimeout(() => controller.abort(), METADATA_PARSE_TIMEOUT_MS)
    try {
      const formData = new FormData()
      formData.append('file', file)
      response = await fetch(endpoint, {
        method: 'POST',
        body: formData,
        signal: controller.signal,
      })
      raw = await response.text()
      try {
        result = raw ? JSON.parse(raw) : null
      } catch {
        result = null
      }
      traceId = String(result?.trace_id || '')

      if (!response.ok && response.status < 500) {
        break
      }
      if (response.ok) {
        break
      }
      lastError = new Error(result?.message || result?.detail || `Metadata parsing failed (${response.status})`)
    } catch (error) {
      if (isAbortLikeError(error)) {
        lastError = new Error(`Metadata parsing timeout after ${Math.round(METADATA_PARSE_TIMEOUT_MS / 1000)}s`)
        break
      }
      lastError = error instanceof Error ? error : new Error('Metadata parsing failed')
    } finally {
      window.clearTimeout(timer)
    }

    if (idx < parseEndpoints.length - 1) {
      console.warn(`[Submission] parse endpoint failed, fallback to next: ${endpoint}`)
    }
  }

  if (!response) {
    throw lastError || new Error('AI parsing failed')
  }

  return { response, raw, result, traceId }
}

export function extractTraceId(error: unknown): string {
  try {
    if (typeof (error as any)?.trace_id === 'string' && (error as any).trace_id) {
      return String((error as any).trace_id)
    }
  } catch {}
  return ''
}

export function isHttpUrl(value: string): boolean {
  return value.startsWith('http://') || value.startsWith('https://')
}

export function hasJournalSelection(journals: Journal[], journalId: string): boolean {
  return journals.length === 0 || journalId.trim().length > 0
}
