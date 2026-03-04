'use client'

import { ArrowLeft } from 'lucide-react'
import Link from 'next/link'

import {
  SubmissionFileUploadCard,
  SubmissionFinalizePanel,
  SubmissionMetadataForm,
  SubmissionWordUploadCard,
  useSubmissionForm,
} from '@/components/submission'

export default function SubmissionForm() {
  const form = useSubmissionForm()

  return (
    <div className="space-y-8">
      <div className="mb-4">
        <Link href="/" className="inline-flex items-center text-sm text-muted-foreground transition-colors hover:text-foreground">
          <ArrowLeft className="mr-2 h-4 w-4" /> Back to Home
        </Link>
      </div>

      <SubmissionMetadataForm
        journals={form.journals}
        isLoadingJournals={form.isLoadingJournals}
        journalLoadError={form.journalLoadError}
        journalId={form.journalId}
        specialIssue={form.specialIssue}
        metadata={{ title: form.metadata.title, abstract: form.metadata.abstract }}
        datasetUrl={form.datasetUrl}
        sourceCodeUrl={form.sourceCodeUrl}
        policyConsent={form.policyConsent}
        ethicsConsent={form.ethicsConsent}
        touched={form.touched}
        showTitleError={form.showTitleError}
        showAbstractError={form.showAbstractError}
        showDatasetError={form.showDatasetError}
        showSourceCodeError={form.showSourceCodeError}
        showJournalError={form.showJournalError}
        showPolicyConsentError={form.showPolicyConsentError}
        showEthicsConsentError={form.showEthicsConsentError}
        onJournalChange={form.onJournalChange}
        onJournalBlur={form.onJournalBlur}
        onSpecialIssueChange={form.onSpecialIssueChange}
        onTitleChange={form.onTitleChange}
        onTitleBlur={form.onTitleBlur}
        onAbstractChange={form.onAbstractChange}
        onAbstractBlur={form.onAbstractBlur}
        onDatasetUrlChange={form.onDatasetUrlChange}
        onDatasetUrlBlur={form.onDatasetUrlBlur}
        onSourceCodeUrlChange={form.onSourceCodeUrlChange}
        onSourceCodeUrlBlur={form.onSourceCodeUrlBlur}
        onPolicyConsentChange={form.onPolicyConsentChange}
        onEthicsConsentChange={form.onEthicsConsentChange}
      />

      <SubmissionWordUploadCard
        isUploadingWordFile={form.isUploadingWordFile}
        wordFilePath={form.wordFilePath}
        wordFileName={form.wordFileName}
        wordFileUploadError={form.wordFileUploadError}
        onWordFileChange={form.handleWordFileUpload}
      />

      <SubmissionFileUploadCard
        fileName={form.fileName}
        isUploading={form.isUploading}
        onFileChange={form.handleFileUpload}
      />

      <SubmissionFinalizePanel
        userEmail={form.userEmail}
        uploadError={form.uploadError}
        parseError={form.parseError}
        isSubmitting={form.isSubmitting}
        submitDisabled={form.submitDisabled}
        showValidationHint={form.showValidationHint}
        onFinalize={form.handleFinalize}
      />
    </div>
  )
}
