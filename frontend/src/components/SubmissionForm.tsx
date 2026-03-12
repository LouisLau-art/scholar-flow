'use client'

import { ArrowLeft } from 'lucide-react'
import Link from 'next/link'

import {
  SubmissionCoverLetterCard,
  SubmissionFileUploadCard,
  SubmissionFinalizePanel,
  SubmissionMetadataForm,
  SubmissionSourceArchiveUploadCard,
  SubmissionSourceTypeSelector,
  SubmissionSourceTypeSwitchDialog,
  SubmissionWordUploadCard,
  useSubmissionForm,
} from '@/components/submission'

export default function SubmissionForm() {
  const form = useSubmissionForm()

  return (
    <div className="space-y-8">
      <div className="mb-4">
        <Link href="/" className="inline-flex items-center text-sm text-foreground/80 transition-colors hover:text-foreground">
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
        submissionEmail={form.metadata.submissionEmail}
        authorContacts={form.authorContacts}
        datasetUrl={form.datasetUrl}
        sourceCodeUrl={form.sourceCodeUrl}
        policyConsent={form.policyConsent}
        ethicsConsent={form.ethicsConsent}
        touched={form.touched}
        showTitleError={form.showTitleError}
        showAbstractError={form.showAbstractError}
        showSubmissionEmailError={form.showSubmissionEmailError}
        showAuthorContactsError={form.showAuthorContactsError}
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
        onSubmissionEmailChange={form.onSubmissionEmailChange}
        onSubmissionEmailBlur={form.onSubmissionEmailBlur}
        onAuthorContactChange={form.onAuthorContactChange}
        onAuthorContactsBlur={form.onAuthorContactsBlur}
        onAddAuthorContact={form.onAddAuthorContact}
        onRemoveAuthorContact={form.onRemoveAuthorContact}
        onMoveAuthorContact={form.onMoveAuthorContact}
        onSelectCorrespondingAuthor={form.onSelectCorrespondingAuthor}
        onDatasetUrlChange={form.onDatasetUrlChange}
        onDatasetUrlBlur={form.onDatasetUrlBlur}
        onSourceCodeUrlChange={form.onSourceCodeUrlChange}
        onSourceCodeUrlBlur={form.onSourceCodeUrlBlur}
        onPolicyConsentChange={form.onPolicyConsentChange}
        onEthicsConsentChange={form.onEthicsConsentChange}
      />

      <SubmissionCoverLetterCard
        isUploadingCoverLetter={form.isUploadingCoverLetter}
        coverLetterPath={form.coverLetterPath}
        coverLetterFileName={form.coverLetterFileName}
        coverLetterUploadError={form.coverLetterUploadError}
        onCoverLetterChange={form.handleCoverLetterUpload}
      />

      <SubmissionSourceTypeSelector
        selectedSourceType={form.selectedSourceType}
        onSourceTypeChange={form.requestSourceTypeChange}
      />

      {form.selectedSourceType === 'word' ? (
        <SubmissionWordUploadCard
          isUploadingWordFile={form.isUploadingWordFile}
          wordFilePath={form.wordFilePath}
          wordFileName={form.wordFileName}
          wordFileUploadError={form.wordFileUploadError}
          inputResetKey={form.wordInputResetKey}
          onWordFileChange={form.handleWordFileUpload}
          onClearWordFile={form.clearWordRoute}
        />
      ) : null}

      {form.selectedSourceType === 'zip' ? (
        <SubmissionSourceArchiveUploadCard
          isUploadingSourceArchive={form.isUploadingSourceArchive}
          sourceArchivePath={form.sourceArchivePath}
          sourceArchiveFileName={form.sourceArchiveFileName}
          sourceArchiveUploadError={form.sourceArchiveUploadError}
          inputResetKey={form.sourceArchiveInputResetKey}
          onSourceArchiveChange={form.handleSourceArchiveUpload}
          onClearSourceArchive={form.clearSourceArchiveRoute}
        />
      ) : null}

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

      <SubmissionSourceTypeSwitchDialog
        open={form.isSourceTypeSwitchDialogOpen}
        pendingSourceType={form.pendingSourceType}
        onConfirm={form.confirmSourceTypeChange}
        onCancel={form.cancelSourceTypeChange}
      />
    </div>
  )
}
