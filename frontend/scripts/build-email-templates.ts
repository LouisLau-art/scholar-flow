import { mkdirSync, writeFileSync } from 'node:fs'
import path from 'node:path'

import { render, toPlainText } from '@react-email/render'

import {
  ReviewerInvitationStandardEmail,
  ReviewerReminderPoliteEmail,
  type ReviewerAssignmentTemplateProps,
} from '../emails/reviewer-assignment'

type EmailTemplateSeedRecord = {
  template_key: string
  display_name: string
  description: string
  scene: string
  event_type: 'none' | 'invitation' | 'reminder'
  subject_template: string
  body_html_template: string
  body_text_template: string
  is_active: boolean
}

const placeholderProps: ReviewerAssignmentTemplateProps = {
  reviewerName: '{{ reviewer_name }}',
  manuscriptTitle: '{{ manuscript_title }}',
  manuscriptId: '{{ manuscript_id }}',
  journalTitle: '{{ journal_title }}',
  dueDate: '{{ due_date }}',
  reviewUrl: '{{ review_url }}',
}

async function buildReviewerTemplates(): Promise<EmailTemplateSeedRecord[]> {
  const invitationHtmlRaw = await render(
    ReviewerInvitationStandardEmail(placeholderProps)
  )
  const reminderHtmlRaw = await render(
    ReviewerReminderPoliteEmail(placeholderProps)
  )
  const invitationHtml = sanitizeRenderedHtml(invitationHtmlRaw)
  const reminderHtml = sanitizeRenderedHtml(reminderHtmlRaw)

  return [
    {
      template_key: 'reviewer_invitation_standard',
      display_name: '审稿邀请信（React Email）',
      description: '由 React Email 生成，可用于审稿邀请。',
      scene: 'reviewer_assignment',
      event_type: 'invitation',
      subject_template: 'Invitation to Review - {{ journal_title }}',
      body_html_template: invitationHtml,
      body_text_template: toPlainText(invitationHtml),
      is_active: true,
    },
    {
      template_key: 'reviewer_reminder_polite',
      display_name: '审稿催促信（React Email）',
      description: '由 React Email 生成，可用于审稿催促。',
      scene: 'reviewer_assignment',
      event_type: 'reminder',
      subject_template: 'Friendly Reminder - {{ journal_title }} Review for {{ manuscript_title }}',
      body_html_template: reminderHtml,
      body_text_template: toPlainText(reminderHtml),
      is_active: true,
    },
  ]
}

function sanitizeRenderedHtml(input: string): string {
  return String(input || '')
    .replaceAll('<!--$-->', '')
    .replaceAll('<!--/$-->', '')
    .replaceAll('<!-- -->', '')
    .replace(/\u0000/g, '')
}

async function main() {
  const output = await buildReviewerTemplates()
  const outputDir = path.resolve(process.cwd(), 'emails/generated')
  mkdirSync(outputDir, { recursive: true })
  const outputPath = path.join(outputDir, 'reviewer-assignment.templates.json')
  writeFileSync(outputPath, JSON.stringify(output, null, 2), 'utf-8')
  console.log(`Generated ${output.length} templates: ${outputPath}`)
}

main().catch((error) => {
  console.error('[build-email-templates] failed:', error)
  process.exit(1)
})
