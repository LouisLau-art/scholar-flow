'use client'

import { format } from 'date-fns'
import { CalendarIcon } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Calendar } from '@/components/ui/calendar'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { cn } from '@/lib/utils'

type DatePickerProps = {
  value?: string
  onChange: (next: string) => void
  placeholder?: string
  minDate?: string
  maxDate?: string
  disabled?: boolean
  className?: string
}

function parseDateInput(value?: string): Date | undefined {
  if (!value) return undefined
  const [year, month, day] = value.split('-').map((part) => Number(part))
  if (!year || !month || !day) return undefined
  const parsed = new Date(year, month - 1, day)
  return Number.isNaN(parsed.getTime()) ? undefined : parsed
}

export function DatePicker({
  value,
  onChange,
  placeholder = 'Pick a date',
  minDate,
  maxDate,
  disabled = false,
  className,
}: DatePickerProps) {
  const selectedDate = parseDateInput(value)
  const min = parseDateInput(minDate)
  const max = parseDateInput(maxDate)

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          disabled={disabled}
          className={cn('w-full justify-between text-left font-normal', !selectedDate && 'text-muted-foreground', className)}
        >
          {selectedDate ? format(selectedDate, 'yyyy-MM-dd') : placeholder}
          <CalendarIcon className="ml-2 h-4 w-4 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
        <Calendar
          mode="single"
          selected={selectedDate}
          onSelect={(next) => {
            if (!next) return
            onChange(format(next, 'yyyy-MM-dd'))
          }}
          disabled={(date) => {
            if (min && date < min) return true
            if (max && date > max) return true
            return false
          }}
          initialFocus
        />
      </PopoverContent>
    </Popover>
  )
}
