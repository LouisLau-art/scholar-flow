'use client'

import { FileArchive, FileText } from 'lucide-react'

import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { cn } from '@/lib/utils'

type SubmissionSourceTypeSelectorProps = {
  selectedSourceType: 'word' | 'zip' | null
  onSourceTypeChange: (nextType: 'word' | 'zip') => void
}

const SOURCE_OPTIONS = [
  {
    value: 'word' as const,
    title: 'Word manuscript (.doc/.docx)',
    description: 'Recommended when you have an editable Word manuscript and want DOCX-first metadata parsing.',
    testId: 'submission-source-type-word',
    icon: FileText,
  },
  {
    value: 'zip' as const,
    title: 'LaTeX source (.zip)',
    description: 'Use this when the manuscript source is LaTeX. ZIP is stored for editorial use and is not parsed for metadata.',
    testId: 'submission-source-type-zip',
    icon: FileArchive,
  },
]

export function SubmissionSourceTypeSelector(props: SubmissionSourceTypeSelectorProps) {
  return (
    <div className="rounded-lg border border-border/80 bg-card p-5">
      <div className="space-y-1">
        <h3 className="text-sm font-semibold text-foreground">Manuscript Source (Choose One)</h3>
        <p className="text-xs text-foreground/70">
          Choose one manuscript source. You can switch later, but switching will remove the currently uploaded source file.
        </p>
      </div>

      <RadioGroup
        value={props.selectedSourceType ?? ''}
        onValueChange={(value) => {
          if (value === 'word' || value === 'zip') {
            props.onSourceTypeChange(value)
          }
        }}
        className="mt-4 grid gap-3"
      >
        {SOURCE_OPTIONS.map((option) => {
          const selected = props.selectedSourceType === option.value
          const Icon = option.icon

          return (
            <label
              key={option.value}
              htmlFor={option.testId}
              className={cn(
                'flex cursor-pointer items-start gap-3 rounded-xl border px-4 py-3 transition-colors',
                selected
                  ? 'border-primary/60 bg-primary/5'
                  : 'border-border/80 bg-background hover:border-primary/35 hover:bg-muted/35',
              )}
            >
              <RadioGroupItem
                id={option.testId}
                value={option.value}
                data-testid={option.testId}
                className="mt-1"
              />
              <Icon className={cn('mt-0.5 h-4 w-4 shrink-0', selected ? 'text-primary' : 'text-foreground/60')} />
              <div className="space-y-1">
                <div className="text-sm font-medium text-foreground">{option.title}</div>
                <p className="text-xs leading-5 text-foreground/70">{option.description}</p>
              </div>
            </label>
          )
        })}
      </RadioGroup>
    </div>
  )
}
