import type { DecisionReport } from '@/types/decision'

export function assembleLetter(reports: DecisionReport[]): string {
  const lines: string[] = [
    'Dear Author,',
    '',
    'Thank you for submitting your manuscript. After considering the reviewer feedback, please see the consolidated comments below.',
    '',
  ]

  reports.forEach((report, index) => {
    const comment = String(report.comments_for_author || '').trim()
    lines.push(`Reviewer ${index + 1}:`)
    lines.push(comment || '(No public comment provided)')
    lines.push('')
  })

  lines.push('Best regards,')
  lines.push('Editorial Office')
  return lines.join('\n')
}
