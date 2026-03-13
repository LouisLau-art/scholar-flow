import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'

import { authService } from '@/services/auth'
import { supabase } from '@/lib/supabase'
import type { Journal } from '@/types/journal'
import {
  INITIAL_METADATA,
  INITIAL_TOUCHED,
  STORAGE_UPLOAD_TIMEOUT_MS,
  SUPPLEMENTAL_UPLOAD_TIMEOUT_MS,
  buildAuthorContactsFromStructuredContacts,
  buildAuthorContactsFromNames,
  createAuthorContact,
  extractTraceId,
  getDuplicateAuthorEmail,
  hasAtLeastOneCorrespondingAuthor,
  hasValidAuthorContacts,
  hasJournalSelection,
  isHttpUrl,
  isSupportedCoverLetterDocument,
  isSupportedSourceArchive,
  isSupportedWordDocument,
  isValidEmail,
  normalizeAuthorContactsForPayload,
  moveAuthorContact,
  parseManuscriptMetadataWithFallback,
  sanitizeFilename,
  type MetadataState,
  type SubmissionAuthorContact,
  type TouchedState,
  withTimeout,
} from './submission-form-utils'

export function useSubmissionForm() {
  const router = useRouter()
  const [isUploading, setIsUploading] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [metadata, setMetadata] = useState<MetadataState>(INITIAL_METADATA)
  const [file, setFile] = useState<File | null>(null)
  const [uploadedPath, setUploadedPath] = useState<string | null>(null)
  const [wordFile, setWordFile] = useState<File | null>(null)
  const [wordFilePath, setWordFilePath] = useState<string | null>(null)
  const [isUploadingWordFile, setIsUploadingWordFile] = useState(false)
  const [wordFileUploadError, setWordFileUploadError] = useState<string | null>(null)
  const [sourceArchiveFile, setSourceArchiveFile] = useState<File | null>(null)
  const [sourceArchivePath, setSourceArchivePath] = useState<string | null>(null)
  const [isUploadingSourceArchive, setIsUploadingSourceArchive] = useState(false)
  const [sourceArchiveUploadError, setSourceArchiveUploadError] = useState<string | null>(null)
  const [hasDocxAutoMetadata, setHasDocxAutoMetadata] = useState(false)
  const [coverLetterFile, setCoverLetterFile] = useState<File | null>(null)
  const [coverLetterPath, setCoverLetterPath] = useState<string | null>(null)
  const [isUploadingCoverLetter, setIsUploadingCoverLetter] = useState(false)
  const [coverLetterUploadError, setCoverLetterUploadError] = useState<string | null>(null)
  const [user, setUser] = useState<any>(null)
  const [journals, setJournals] = useState<Journal[]>([])
  const [isLoadingJournals, setIsLoadingJournals] = useState(false)
  const [journalLoadError, setJournalLoadError] = useState<string | null>(null)
  const [journalId, setJournalId] = useState('')
  const [specialIssue, setSpecialIssue] = useState('')
  const [touched, setTouched] = useState<TouchedState>(INITIAL_TOUCHED)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [parseError, setParseError] = useState<string | null>(null)
  const [datasetUrl, setDatasetUrl] = useState('')
  const [sourceCodeUrl, setSourceCodeUrl] = useState('')
  const [policyConsent, setPolicyConsent] = useState(false)
  const [ethicsConsent, setEthicsConsent] = useState(false)
  const [wordInputResetKey, setWordInputResetKey] = useState(0)
  const [sourceArchiveInputResetKey, setSourceArchiveInputResetKey] = useState(0)
  const [selectedSourceType, setSelectedSourceType] = useState<'word' | 'zip' | null>(null)
  const [pendingSourceType, setPendingSourceType] = useState<'word' | 'zip' | null>(null)
  const [isSourceTypeSwitchDialogOpen, setIsSourceTypeSwitchDialogOpen] = useState(false)

  const titleValid = metadata.title.trim().length >= 5
  const abstractValid = metadata.abstract.trim().length >= 30
  const submissionEmailValue = metadata.submissionEmail.trim()
  const submissionEmailValid = isValidEmail(submissionEmailValue)
  const duplicateAuthorEmail = getDuplicateAuthorEmail(metadata.authorContacts)
  const authorContactsValid = hasValidAuthorContacts(metadata.authorContacts)
  const fileValid = !!uploadedPath
  const wordFileValid = !!wordFilePath
  const sourceArchiveValid = !!sourceArchivePath
  const hasExclusiveSourceUpload = wordFileValid !== sourceArchiveValid
  const selectedSourceUploadValid =
    selectedSourceType === 'word'
      ? wordFileValid
      : selectedSourceType === 'zip'
        ? sourceArchiveValid
        : false
  const manuscriptSourceValid = hasExclusiveSourceUpload && selectedSourceUploadValid
  const coverLetterValid = !!coverLetterPath
  const datasetValue = datasetUrl.trim()
  const sourceCodeValue = sourceCodeUrl.trim()
  const journalValid = hasJournalSelection(journals, journalId)
  const datasetUrlValid = datasetValue === '' || isHttpUrl(datasetValue)
  const sourceCodeUrlValid = sourceCodeValue === '' || isHttpUrl(sourceCodeValue)
  const showTitleError = touched.title && !titleValid
  const showAbstractError = touched.abstract && !abstractValid
  const showSubmissionEmailError = touched.submissionEmail && !submissionEmailValid
  const showAuthorContactsError = touched.authorContacts && !authorContactsValid
  const showDatasetError = touched.datasetUrl && !datasetUrlValid
  const showSourceCodeError = touched.sourceCodeUrl && !sourceCodeUrlValid
  const showJournalError = touched.journal && !journalValid
  const showPolicyConsentError = touched.policyConsent && !policyConsent
  const showEthicsConsentError = touched.ethicsConsent && !ethicsConsent

  useEffect(() => {
    const checkUser = async () => {
      const session = await authService.getSession()
      if (session?.user) {
        setUser(session.user)
        setMetadata((prev) =>
          prev.submissionEmail.trim().length > 0
            ? prev
            : {
                ...prev,
                submissionEmail: String(session.user.email || '').trim(),
              },
        )
      } else {
        toast.error('Please log in to submit a manuscript')
      }
    }
    checkUser()

    const { data: { subscription } } = authService.onAuthStateChange((session) => {
      setUser(session?.user || null)
    })

    return () => subscription.unsubscribe()
  }, [])

  useEffect(() => {
    let cancelled = false

    const loadJournals = async () => {
      setIsLoadingJournals(true)
      setJournalLoadError(null)
      try {
        const response = await fetch('/api/v1/public/journals')
        const payload = await response.json().catch(() => null)
        if (!response.ok || !payload?.success) {
          throw new Error(payload?.detail || payload?.message || 'Failed to load journals')
        }
        const rows = Array.isArray(payload.data) ? payload.data : []
        if (!cancelled) {
          setJournals(rows)
          if (rows.length === 1) {
            setJournalId(String(rows[0]?.id || ''))
          }
        }
      } catch (error) {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : 'Failed to load journals'
          setJournalLoadError(message)
        }
      } finally {
        if (!cancelled) {
          setIsLoadingJournals(false)
        }
      }
    }

    loadJournals()
    return () => {
      cancelled = true
    }
  }, [])

  const markTouched = (field: keyof TouchedState) => {
    setTouched((prev) => (prev[field] ? prev : { ...prev, [field]: true }))
  }

  const applyParsedMetadata = (payload: any, source: 'pdf' | 'docx') => {
    const parsedTitle = String(payload?.title || '').trim()
    const parsedAbstract = String(payload?.abstract || '').trim()
    const parsedAuthors = Array.isArray(payload?.authors)
      ? payload.authors.map((item: unknown) => String(item || '').trim()).filter(Boolean).slice(0, 20)
      : []
    const parsedAuthorContacts = Array.isArray(payload?.author_contacts)
      ? payload.author_contacts
          .filter((item: unknown) => item && typeof item === 'object')
          .slice(0, 20)
      : []

    setMetadata((prev) => {
      const next = { ...prev }
      if (source === 'docx') {
        if (!touched.title && parsedTitle) {
          next.title = parsedTitle
        }
        if (!touched.abstract && parsedAbstract) {
          next.abstract = parsedAbstract
        }
      } else {
        if (!hasDocxAutoMetadata && !touched.title && parsedTitle) {
          next.title = parsedTitle
        }
        if (!hasDocxAutoMetadata && !touched.abstract && parsedAbstract) {
          next.abstract = parsedAbstract
        }
      }
      if (!touched.authorContacts) {
        if (parsedAuthorContacts.length > 0) {
          next.authorContacts = buildAuthorContactsFromStructuredContacts(parsedAuthorContacts)
        } else if (parsedAuthors.length > 0) {
          next.authorContacts = buildAuthorContactsFromNames(parsedAuthors)
        }
      }
      return next
    })

    if (source === 'docx' && (parsedTitle || parsedAbstract)) {
      setHasDocxAutoMetadata(true)
    }
  }

  const describeParserSource = (parserSource: unknown) => {
    const value = String(parserSource || '').trim().toLowerCase()
    if (value === 'gemini') return 'Metadata parsed with Gemini.'
    if (value === 'gemini+local_fill') return 'Metadata parsed with Gemini and local fallback.'
    if (value === 'local') return 'Metadata parsed with the local fallback parser.'
    if (value === 'timeout') return 'Metadata parsing timed out. Please review manually.'
    return ''
  }

  const clearWordRoute = (options?: { resetInput?: boolean }) => {
    setWordFile(null)
    setWordFilePath(null)
    setWordFileUploadError(null)
    if (hasDocxAutoMetadata) {
      setMetadata((prev) => ({
        ...prev,
        title: touched.title ? prev.title : '',
        abstract: touched.abstract ? prev.abstract : '',
        authorContacts: touched.authorContacts ? prev.authorContacts : [createAuthorContact({ isCorresponding: true })],
      }))
    }
    setHasDocxAutoMetadata(false)
    if (options?.resetInput) {
      setWordInputResetKey((value) => value + 1)
    }
  }

  const clearSourceArchiveRoute = (options?: { resetInput?: boolean }) => {
    setSourceArchiveFile(null)
    setSourceArchivePath(null)
    setSourceArchiveUploadError(null)
    if (options?.resetInput) {
      setSourceArchiveInputResetKey((value) => value + 1)
    }
  }

  const requestSourceTypeChange = (nextType: 'word' | 'zip') => {
    if (selectedSourceType === nextType) {
      return
    }

    const hasCurrentSourceFile =
      (selectedSourceType === 'word' && (wordFile !== null || wordFilePath !== null)) ||
      (selectedSourceType === 'zip' && (sourceArchiveFile !== null || sourceArchivePath !== null))

    if (hasCurrentSourceFile) {
      setPendingSourceType(nextType)
      setIsSourceTypeSwitchDialogOpen(true)
      return
    }

    setPendingSourceType(null)
    setIsSourceTypeSwitchDialogOpen(false)
    setSelectedSourceType(nextType)
  }

  const cancelSourceTypeChange = () => {
    setPendingSourceType(null)
    setIsSourceTypeSwitchDialogOpen(false)
  }

  const confirmSourceTypeChange = () => {
    if (selectedSourceType === 'word') {
      clearWordRoute({ resetInput: true })
    } else if (selectedSourceType === 'zip') {
      clearSourceArchiveRoute({ resetInput: true })
    }

    setSelectedSourceType(pendingSourceType)
    setPendingSourceType(null)
    setIsSourceTypeSwitchDialogOpen(false)
  }

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0]
    if (!selectedFile) return

    const isPdf = selectedFile.type === 'application/pdf' || selectedFile.name.toLowerCase().endsWith('.pdf')
    if (!isPdf) {
      setFile(null)
      setUploadedPath(null)
      setUploadError(null)
      setParseError(null)
      event.currentTarget.value = ''
      toast.error('Only PDF files are supported.')
      return
    }

    if (!user) {
      toast.error('Please log in to upload a manuscript.')
      return
    }

    setFile(selectedFile)
    setUploadedPath(null)
    setUploadError(null)
    setParseError(null)
    setIsUploading(true)
    const toastId = toast.loading('Uploading and analyzing manuscript...')

    try {
      const uploadPath = `${user.id}/${crypto.randomUUID()}.pdf`
      const { error: uploadErrorResult } = await withTimeout(
        supabase.storage
          .from('manuscripts')
          .upload(uploadPath, selectedFile, {
            contentType: 'application/pdf',
            upsert: false,
          }),
        STORAGE_UPLOAD_TIMEOUT_MS,
        'Storage upload',
      )
      if (uploadErrorResult) {
        throw new Error(`Upload failed: ${uploadErrorResult.message}`)
      }
      setUploadedPath(uploadPath)
      if (hasDocxAutoMetadata) {
        toast.success('PDF uploaded. Word metadata remains the primary source.', { id: toastId })
        return
      }

      toast.loading('File uploaded. Extracting metadata...', { id: toastId })

      const { response, raw, result, traceId: parseTraceId } = await parseManuscriptMetadataWithFallback(selectedFile)

      if (!response.ok) {
        const message = result?.message || result?.detail || (raw && raw.length < 500 ? raw : '') || 'AI parsing failed'
        const error: any = new Error(message)
        if (parseTraceId) error.trace_id = parseTraceId
        throw error
      }

      if (!result) {
        const error: any = new Error('AI parsing failed: invalid response')
        if (parseTraceId) error.trace_id = parseTraceId
        throw error
      }

      if (result.success) {
        applyParsedMetadata(result.data, 'pdf')
        if (result.message) {
          const info = parseTraceId ? `${result.message}（trace: ${parseTraceId}）` : result.message
          toast.success(info, { id: toastId })
        } else {
          const parserInfo = describeParserSource(result?.data?.parser_source)
          const baseInfo = parserInfo || 'AI parsing successful!'
          const info = parseTraceId ? `${baseInfo}（trace: ${parseTraceId}）` : baseInfo
          toast.success(info, { id: toastId })
        }
      } else {
        const error: any = new Error(result.message || 'AI parsing failed')
        if (parseTraceId) error.trace_id = parseTraceId
        throw error
      }
    } catch (error) {
      console.error('Parsing failed:', error)
      const lowered = String((error as any)?.message || '').toLowerCase()
      const message =
        (error instanceof DOMException && error.name === 'AbortError') || lowered.includes('timeout')
          ? '解析超时（>25s），已跳过 AI 预填，请手动填写标题与摘要。'
          : error instanceof Error
            ? error.message
            : 'AI parsing failed'
      const traceInError = extractTraceId(error)
      const finalMessage = traceInError ? `${message}（trace: ${traceInError}）` : message
      toast.error(finalMessage, { id: toastId })
      if (message.toLowerCase().includes('upload failed')) {
        setUploadError(message.replace('Upload failed: ', ''))
      } else {
        setParseError(finalMessage)
      }
    } finally {
      setIsUploading(false)
    }
  }

  const handleWordFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0]
    if (!selectedFile) {
      clearWordRoute({ resetInput: true })
      return
    }

    if (selectedSourceType !== 'word') {
      event.currentTarget.value = ''
      toast.error('Choose Word manuscript as the source type before uploading the file.')
      return
    }

    if (!isSupportedWordDocument(selectedFile)) {
      setWordFile(null)
      setWordFilePath(null)
      setWordFileUploadError(null)
      event.currentTarget.value = ''
      toast.error('Word manuscript only supports .doc/.docx files.')
      return
    }

    if (!user) {
      toast.error('Please log in to upload the Word manuscript.')
      return
    }

    setWordFile(selectedFile)
    setWordFilePath(null)
    setWordFileUploadError(null)
    setIsUploadingWordFile(true)
    const toastId = toast.loading('Uploading Word manuscript…')

    try {
      const safeName = sanitizeFilename(selectedFile.name || 'manuscript')
      const extension = safeName.toLowerCase().endsWith('.doc') ? '.doc' : '.docx'
      const uploadPath = `${user.id}/word-manuscripts/${crypto.randomUUID()}_${safeName.replace(/\.(doc|docx)$/i, '')}${extension}`
      const { error: uploadErrorResult } = await withTimeout(
        supabase.storage
          .from('manuscripts')
          .upload(uploadPath, selectedFile, {
            contentType: selectedFile.type || 'application/octet-stream',
            upsert: false,
          }),
        SUPPLEMENTAL_UPLOAD_TIMEOUT_MS,
        'Word manuscript upload',
      )
      if (uploadErrorResult) {
        throw new Error(`Upload failed: ${uploadErrorResult.message}`)
      }

      setWordFilePath(uploadPath)

      let successMessage = 'Word manuscript uploaded.'
      try {
        const { response, result, traceId: parseTraceId } = await parseManuscriptMetadataWithFallback(selectedFile)
        if (response.ok && result?.success) {
          applyParsedMetadata(result?.data || {}, 'docx')
          const parsedTitle = String(result?.data?.title || '').trim()
          const parsedAbstract = String(result?.data?.abstract || '').trim()
          const parserInfo = describeParserSource(result?.data?.parser_source)
          if (parsedTitle || parsedAbstract) {
            const baseInfo = parserInfo || 'Metadata parsed from DOCX.'
            successMessage = parseTraceId
              ? `Word manuscript uploaded. ${baseInfo}（trace: ${parseTraceId}）`
              : `Word manuscript uploaded. ${baseInfo}`
          } else if (result?.message) {
            successMessage = `Word manuscript uploaded. ${String(result.message)}`
          } else if (parserInfo) {
            successMessage = `Word manuscript uploaded. ${parserInfo}`
          }
        }
      } catch (parseError) {
        console.warn('Word metadata parsing skipped:', parseError)
      }

      toast.success(successMessage, { id: toastId })
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Word manuscript upload failed.'
      setWordFileUploadError(message.replace('Upload failed: ', ''))
      toast.error(message, { id: toastId })
    } finally {
      setIsUploadingWordFile(false)
    }
  }

  const handleSourceArchiveUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0]
    if (!selectedFile) {
      clearSourceArchiveRoute({ resetInput: true })
      return
    }

    if (selectedSourceType !== 'zip') {
      event.currentTarget.value = ''
      toast.error('Choose LaTeX source ZIP as the source type before uploading the file.')
      return
    }

    if (!isSupportedSourceArchive(selectedFile)) {
      clearSourceArchiveRoute({ resetInput: true })
      event.currentTarget.value = ''
      toast.error('LaTeX source archive only supports .zip files.')
      return
    }

    if (!user) {
      toast.error('Please log in to upload the LaTeX source ZIP.')
      return
    }

    setSourceArchiveFile(selectedFile)
    setSourceArchivePath(null)
    setSourceArchiveUploadError(null)
    setIsUploadingSourceArchive(true)
    const toastId = toast.loading('Uploading LaTeX source ZIP…')

    try {
      const safeName = sanitizeFilename(selectedFile.name || 'latex-source.zip')
      const uploadPath = `${user.id}/source-archives/${crypto.randomUUID()}_${safeName.replace(/\.zip$/i, '')}.zip`
      const { error: uploadErrorResult } = await withTimeout(
        supabase.storage
          .from('manuscripts')
          .upload(uploadPath, selectedFile, {
            contentType: selectedFile.type || 'application/zip',
            upsert: false,
          }),
        SUPPLEMENTAL_UPLOAD_TIMEOUT_MS,
        'LaTeX source ZIP upload',
      )
      if (uploadErrorResult) {
        throw new Error(`Upload failed: ${uploadErrorResult.message}`)
      }

      setSourceArchivePath(uploadPath)
      toast.success('LaTeX source ZIP uploaded. It will be stored for editorial use only.', { id: toastId })
    } catch (error) {
      const message = error instanceof Error ? error.message : 'LaTeX source ZIP upload failed.'
      setSourceArchiveUploadError(message.replace('Upload failed: ', ''))
      toast.error(message, { id: toastId })
    } finally {
      setIsUploadingSourceArchive(false)
    }
  }

  const handleCoverLetterUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0]
    if (!selectedFile) {
      setCoverLetterFile(null)
      setCoverLetterPath(null)
      setCoverLetterUploadError(null)
      return
    }

    if (!isSupportedCoverLetterDocument(selectedFile)) {
      setCoverLetterFile(null)
      setCoverLetterPath(null)
      setCoverLetterUploadError(null)
      event.currentTarget.value = ''
      toast.error('Cover letter only supports .pdf/.doc/.docx files.')
      return
    }

    if (!user) {
      toast.error('Please log in to upload the cover letter.')
      return
    }

    setCoverLetterFile(selectedFile)
    setCoverLetterPath(null)
    setCoverLetterUploadError(null)
    setIsUploadingCoverLetter(true)
    const toastId = toast.loading('Uploading cover letter…')

    try {
      const safeName = sanitizeFilename(selectedFile.name || 'cover-letter')
      const lowered = safeName.toLowerCase()
      const extension = lowered.endsWith('.pdf') ? '.pdf' : lowered.endsWith('.doc') ? '.doc' : '.docx'
      const uploadPath = `${user.id}/cover-letters/${crypto.randomUUID()}_${safeName.replace(/\.(pdf|doc|docx)$/i, '')}${extension}`
      const { error: uploadErrorResult } = await withTimeout(
        supabase.storage
          .from('manuscripts')
          .upload(uploadPath, selectedFile, {
            contentType: selectedFile.type || 'application/octet-stream',
            upsert: false,
          }),
        SUPPLEMENTAL_UPLOAD_TIMEOUT_MS,
        'Cover letter upload',
      )
      if (uploadErrorResult) {
        throw new Error(`Upload failed: ${uploadErrorResult.message}`)
      }

      setCoverLetterPath(uploadPath)
      toast.success('Cover letter uploaded.', { id: toastId })
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Cover letter upload failed.'
      setCoverLetterUploadError(message.replace('Upload failed: ', ''))
      toast.error(message, { id: toastId })
    } finally {
      setIsUploadingCoverLetter(false)
    }
  }

  const handleFinalize = async () => {
    setTouched((prev) => ({
      ...prev,
      submissionEmail: true,
      authorContacts: true,
      policyConsent: true,
      ethicsConsent: true,
    }))

    if (!file) {
      toast.error('Please select a PDF file before submitting.')
      return
    }
    if (!uploadedPath) {
      toast.error('File upload is incomplete. Please try again.')
      return
    }
    if (!selectedSourceType) {
      toast.error('Please choose one manuscript source before submitting.')
      return
    }
    if (selectedSourceType === 'word' && wordFile && !wordFilePath) {
      toast.error('Word manuscript upload is incomplete. Please try again.')
      return
    }
    if (selectedSourceType === 'zip' && sourceArchiveFile && !sourceArchivePath) {
      toast.error('LaTeX source ZIP upload is incomplete. Please try again.')
      return
    }
    if (selectedSourceType === 'word' && !wordFilePath) {
      toast.error('Please upload the Word manuscript before submitting.')
      return
    }
    if (selectedSourceType === 'zip' && !sourceArchivePath) {
      toast.error('Please upload the LaTeX source ZIP before submitting.')
      return
    }
    if (wordFilePath && sourceArchivePath) {
      toast.error('Please keep only one manuscript source: Word manuscript or LaTeX source ZIP.')
      return
    }
    if (!coverLetterFile) {
      toast.error('Please upload the cover letter before submitting.')
      return
    }
    if (!coverLetterPath) {
      toast.error('Cover letter upload is incomplete. Please try again.')
      return
    }
    if (!titleValid) {
      toast.error('Title must be at least 5 characters.')
      return
    }
    if (!abstractValid) {
      toast.error('Abstract must be at least 30 characters.')
      return
    }
    if (!submissionEmailValid) {
      toast.error('Please provide a valid submission email.')
      return
    }
    if (!authorContactsValid) {
      if (duplicateAuthorEmail) {
        toast.error('Each author email must be unique.')
      } else if (!hasAtLeastOneCorrespondingAuthor(metadata.authorContacts)) {
        toast.error('Please select at least one corresponding author.')
      } else {
        toast.error('Please complete every author with name, email, affiliation, city, and country or region.')
      }
      return
    }
    if (!datasetUrlValid) {
      toast.error('Dataset URL must start with http:// or https://.')
      return
    }
    if (!sourceCodeUrlValid) {
      toast.error('Source code URL must start with http:// or https://.')
      return
    }
    if (isLoadingJournals) {
      toast.error('Journal list is still loading. Please wait a moment.')
      return
    }
    if (!journalValid) {
      toast.error('Please select a target journal before finalizing submission.')
      return
    }
    if (journals.length === 0) {
      toast.error('No active journals available. Please contact admin.')
      return
    }
    if (!policyConsent) {
      toast.error('Please confirm submission policy and publication terms before finalizing.')
      return
    }
    if (!ethicsConsent) {
      toast.error('Please confirm ethics and compliance declaration before finalizing.')
      return
    }
    if (!user) {
      toast.error('Please log in to submit a manuscript')
      return
    }

    setIsSubmitting(true)
    const toastId = toast.loading('Saving manuscript to database...')

    try {
      const accessToken = await authService.getAccessToken()
      if (!accessToken) {
        throw new Error('No authentication token available')
      }

      const response = await fetch('/api/v1/manuscripts', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          title: metadata.title,
          abstract: metadata.abstract,
          submission_email: submissionEmailValue,
          author_contacts: normalizeAuthorContactsForPayload(metadata.authorContacts),
          author_id: user.id,
          file_path: uploadedPath,
          manuscript_word_path: wordFilePath,
          manuscript_word_filename: wordFile?.name || null,
          manuscript_word_content_type: wordFile?.type || null,
          source_archive_path: sourceArchivePath,
          source_archive_filename: sourceArchiveFile?.name || null,
          source_archive_content_type: sourceArchiveFile?.type || null,
          cover_letter_path: coverLetterPath,
          cover_letter_filename: coverLetterFile?.name || null,
          cover_letter_content_type: coverLetterFile?.type || null,
          dataset_url: datasetValue || null,
          source_code_url: sourceCodeValue || null,
          journal_id: journalId || null,
          special_issue: specialIssue.trim() || null,
        }),
      })
      const result = await response.json()

      if (result.success) {
        toast.success('Manuscript submitted successfully!', { id: toastId })
        router.push('/dashboard')
      } else {
        throw new Error(result.message || 'Persistence failed')
      }
    } catch (error) {
      console.error('Submission failed:', error)
      toast.error('Failed to save. Check database connection.', { id: toastId })
    } finally {
      setIsSubmitting(false)
    }
  }

  return {
    userEmail: user?.email || null,
    fileName: file?.name || null,
    wordFileName: wordFile?.name || null,
    wordFilePath,
    wordFileUploadError,
    isUploadingWordFile,
    sourceArchiveFileName: sourceArchiveFile?.name || null,
    sourceArchivePath,
    sourceArchiveUploadError,
    isUploadingSourceArchive,
    coverLetterFileName: coverLetterFile?.name || null,
    coverLetterPath,
    coverLetterUploadError,
    isUploadingCoverLetter,
    isUploading,
    isSubmitting,
    uploadError,
    parseError,
    journals,
    isLoadingJournals,
    journalLoadError,
    journalId,
    specialIssue,
    metadata,
    datasetUrl,
    sourceCodeUrl,
    policyConsent,
    ethicsConsent,
    touched,
    showTitleError,
    showAbstractError,
    showSubmissionEmailError,
    showAuthorContactsError,
    showDatasetError,
    showSourceCodeError,
    showJournalError,
    showPolicyConsentError,
    showEthicsConsentError,
    duplicateAuthorEmail,
    submitDisabled:
      !fileValid ||
      !manuscriptSourceValid ||
      !coverLetterValid ||
      !titleValid ||
      !abstractValid ||
      !submissionEmailValid ||
      !authorContactsValid ||
      !journalValid ||
      !datasetUrlValid ||
      !sourceCodeUrlValid ||
      !policyConsent ||
      !ethicsConsent ||
      isLoadingJournals ||
      isUploading ||
      isUploadingWordFile ||
      isUploadingSourceArchive ||
      isUploadingCoverLetter ||
      isSubmitting ||
      !user,
    showValidationHint:
      !!user &&
      (!fileValid ||
        !manuscriptSourceValid ||
        !coverLetterValid ||
        !titleValid ||
        !abstractValid ||
        !submissionEmailValid ||
        !authorContactsValid ||
        !journalValid ||
        !datasetUrlValid ||
        !sourceCodeUrlValid ||
        !policyConsent ||
        !ethicsConsent),
    handleFileUpload,
    handleWordFileUpload,
    handleSourceArchiveUpload,
    handleCoverLetterUpload,
    handleFinalize,
    selectedSourceType,
    requestSourceTypeChange,
    pendingSourceType,
    isSourceTypeSwitchDialogOpen,
    confirmSourceTypeChange,
    cancelSourceTypeChange,
    clearWordRoute: () => clearWordRoute({ resetInput: true }),
    clearSourceArchiveRoute: () => clearSourceArchiveRoute({ resetInput: true }),
    wordInputResetKey,
    sourceArchiveInputResetKey,
    onJournalChange: (value: string) => {
      setJournalId(value)
      markTouched('journal')
    },
    onJournalBlur: () => markTouched('journal'),
    onSpecialIssueChange: (value: string) => {
      setSpecialIssue(value)
    },
    onTitleChange: (value: string) => {
      setMetadata((prev) => ({ ...prev, title: value }))
      markTouched('title')
    },
    onTitleBlur: () => markTouched('title'),
    onAbstractChange: (value: string) => {
      setMetadata((prev) => ({ ...prev, abstract: value }))
      markTouched('abstract')
    },
    onAbstractBlur: () => markTouched('abstract'),
    onSubmissionEmailChange: (value: string) => {
      setMetadata((prev) => ({ ...prev, submissionEmail: value }))
      markTouched('submissionEmail')
    },
    onSubmissionEmailBlur: () => markTouched('submissionEmail'),
    authorContacts: metadata.authorContacts,
    onAuthorContactChange: (
      authorId: string,
      field: keyof Pick<SubmissionAuthorContact, 'name' | 'email' | 'affiliation' | 'city' | 'countryOrRegion'>,
      value: string,
    ) => {
      setMetadata((prev) => ({
        ...prev,
        authorContacts: prev.authorContacts.map((author) =>
          author.id === authorId ? { ...author, [field]: value } : author,
        ),
      }))
      markTouched('authorContacts')
    },
    onAddAuthorContact: () => {
      setMetadata((prev) => ({
        ...prev,
        authorContacts: [...prev.authorContacts, createAuthorContact()],
      }))
      markTouched('authorContacts')
    },
    onRemoveAuthorContact: (authorId: string) => {
      setMetadata((prev) => {
        if (prev.authorContacts.length <= 1) {
          return prev
        }
        const remaining = prev.authorContacts.filter((author) => author.id !== authorId)
        if (!remaining.some((author) => author.isCorresponding) && remaining[0]) {
          remaining[0] = { ...remaining[0], isCorresponding: true }
        }
        return {
          ...prev,
          authorContacts: remaining,
        }
      })
      markTouched('authorContacts')
    },
    onMoveAuthorContact: (authorId: string, direction: 'up' | 'down') => {
      setMetadata((prev) => ({
        ...prev,
        authorContacts: moveAuthorContact(prev.authorContacts, authorId, direction),
      }))
      markTouched('authorContacts')
    },
    onSelectCorrespondingAuthor: (authorId: string) => {
      setMetadata((prev) => ({
        ...prev,
        authorContacts: prev.authorContacts.map((author) =>
          author.id === authorId ? { ...author, isCorresponding: !author.isCorresponding } : author,
        ),
      }))
      markTouched('authorContacts')
    },
    onAuthorContactsBlur: () => markTouched('authorContacts'),
    onDatasetUrlChange: (value: string) => {
      setDatasetUrl(value)
      markTouched('datasetUrl')
    },
    onDatasetUrlBlur: () => markTouched('datasetUrl'),
    onSourceCodeUrlChange: (value: string) => {
      setSourceCodeUrl(value)
      markTouched('sourceCodeUrl')
    },
    onSourceCodeUrlBlur: () => markTouched('sourceCodeUrl'),
    onPolicyConsentChange: (value: boolean) => {
      setPolicyConsent(value)
      markTouched('policyConsent')
    },
    onEthicsConsentChange: (value: boolean) => {
      setEthicsConsent(value)
      markTouched('ethicsConsent')
    },
  }
}
