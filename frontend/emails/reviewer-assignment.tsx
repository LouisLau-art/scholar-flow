import {
  Body,
  Button,
  Container,
  Head,
  Heading,
  Hr,
  Html,
  Section,
  Text,
} from '@react-email/components'
import type { ReactNode } from 'react'

export type ReviewerAssignmentTemplateProps = {
  reviewerName: string
  manuscriptTitle: string
  manuscriptId: string
  journalTitle: string
  dueDate: string
  reviewUrl?: string
  cancelReason?: string
}

const style = {
  body: {
    backgroundColor: '#f3f6fb',
    color: '#0f172a',
    fontFamily: 'Arial, "Helvetica Neue", Helvetica, sans-serif',
    margin: 0,
    padding: '24px 0',
  },
  container: {
    backgroundColor: '#ffffff',
    border: '1px solid #dbe3f1',
    borderRadius: '12px',
    margin: '0 auto',
    maxWidth: '640px',
    padding: '28px 24px',
  },
  badge: {
    color: '#2563eb',
    fontSize: '12px',
    fontWeight: 700,
    letterSpacing: '0.08em',
    margin: 0,
    textTransform: 'uppercase' as const,
  },
  heading: {
    color: '#0b1a34',
    fontSize: '22px',
    fontWeight: 700,
    lineHeight: '1.35',
    margin: '10px 0 14px',
  },
  paragraph: {
    color: '#334155',
    fontSize: '15px',
    lineHeight: '1.7',
    margin: '10px 0',
  },
  metaBox: {
    backgroundColor: '#f8fbff',
    border: '1px solid #e2ebfa',
    borderRadius: '10px',
    marginTop: '16px',
    padding: '14px 16px',
  },
  metaLabel: {
    color: '#64748b',
    fontSize: '12px',
    letterSpacing: '0.06em',
    margin: 0,
    textTransform: 'uppercase' as const,
  },
  metaValue: {
    color: '#0f172a',
    fontSize: '14px',
    fontWeight: 600,
    lineHeight: '1.5',
    margin: '4px 0 0',
  },
  cta: {
    backgroundColor: '#2563eb',
    borderRadius: '9px',
    boxSizing: 'border-box' as const,
    color: '#ffffff',
    display: 'inline-block',
    fontSize: '14px',
    fontWeight: 700,
    lineHeight: '1',
    marginTop: '18px',
    padding: '12px 18px',
    textDecoration: 'none',
  },
  footnote: {
    color: '#94a3b8',
    fontSize: '12px',
    lineHeight: '1.6',
    margin: '12px 0 0',
  },
}

function ReviewerMailLayout({
  children,
}: {
  children: ReactNode
}) {
  return (
    <Html lang="en">
      <Head />
      <Body style={style.body}>
        <Container style={style.container}>{children}</Container>
      </Body>
    </Html>
  )
}

export function ReviewerInvitationStandardEmail({
  reviewerName,
  manuscriptTitle,
  manuscriptId,
  journalTitle,
  dueDate,
  reviewUrl,
}: ReviewerAssignmentTemplateProps) {
  return (
    <ReviewerMailLayout>
      <Text style={style.badge}>Peer Review Invitation</Text>
      <Heading style={style.heading}>Invitation to Review</Heading>
      <Text style={style.paragraph}>Dear {reviewerName},</Text>
      <Text style={style.paragraph}>
        You are invited to review the manuscript <strong>{manuscriptTitle}</strong> for{' '}
        <strong>{journalTitle}</strong>.
      </Text>
      <Section style={style.metaBox}>
        <Text style={style.metaLabel}>Manuscript ID</Text>
        <Text style={style.metaValue}>{manuscriptId}</Text>
        <Text style={style.metaLabel}>Requested Due Date</Text>
        <Text style={style.metaValue}>{dueDate}</Text>
      </Section>
      <Button href={reviewUrl} style={style.cta}>
        Open Invitation
      </Button>
      <Hr style={{ borderColor: '#e2e8f0', margin: '20px 0 14px' }} />
      <Text style={style.footnote}>
        If the button cannot be clicked, copy and open this link:
        <br />
        {reviewUrl}
      </Text>
    </ReviewerMailLayout>
  )
}

export function ReviewerReminderPoliteEmail({
  reviewerName,
  manuscriptTitle,
  manuscriptId,
  journalTitle,
  dueDate,
  reviewUrl,
}: ReviewerAssignmentTemplateProps) {
  return (
    <ReviewerMailLayout>
      <Text style={style.badge}>Review Reminder</Text>
      <Heading style={style.heading}>Friendly Reminder for Your Review</Heading>
      <Text style={style.paragraph}>Dear {reviewerName},</Text>
      <Text style={style.paragraph}>
        This is a friendly reminder about your review for{' '}
        <strong>{manuscriptTitle}</strong> in <strong>{journalTitle}</strong>.
      </Text>
      <Section style={style.metaBox}>
        <Text style={style.metaLabel}>Manuscript ID</Text>
        <Text style={style.metaValue}>{manuscriptId}</Text>
        <Text style={style.metaLabel}>Current Due Date</Text>
        <Text style={style.metaValue}>{dueDate}</Text>
      </Section>
      <Button href={reviewUrl} style={style.cta}>
        Continue Review
      </Button>
      <Hr style={{ borderColor: '#e2e8f0', margin: '20px 0 14px' }} />
      <Text style={style.footnote}>
        Thanks again for supporting our editorial process.
        <br />
        Link: {reviewUrl}
      </Text>
    </ReviewerMailLayout>
  )
}

export function ReviewerCancellationStandardEmail({
  reviewerName,
  manuscriptTitle,
  manuscriptId,
  journalTitle,
  cancelReason,
}: ReviewerAssignmentTemplateProps) {
  return (
    <ReviewerMailLayout>
      <Text style={style.badge}>Review Update</Text>
      <Heading style={style.heading}>Review Assignment Cancelled</Heading>
      <Text style={style.paragraph}>Dear {reviewerName},</Text>
      <Text style={style.paragraph}>
        Your review assignment for <strong>{manuscriptTitle}</strong> in <strong>{journalTitle}</strong> has been
        cancelled.
      </Text>
      <Section style={style.metaBox}>
        <Text style={style.metaLabel}>Manuscript ID</Text>
        <Text style={style.metaValue}>{manuscriptId}</Text>
        <Text style={style.metaLabel}>Reason</Text>
        <Text style={style.metaValue}>{cancelReason || 'Editorial workflow updated.'}</Text>
      </Section>
      <Hr style={{ borderColor: '#e2e8f0', margin: '20px 0 14px' }} />
      <Text style={style.footnote}>
        No further action is required. If you already started drafting comments, please disregard the earlier
        invitation link.
      </Text>
    </ReviewerMailLayout>
  )
}
