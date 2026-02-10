'use client'

import { format } from 'date-fns'
import { CalendarIcon } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Calendar } from '@/components/ui/calendar'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { cn } from '@/lib/utils'

type DateTimePickerProps = {
  value?: string
  onChange: (next: string) => void
  placeholder?: string
  disabled?: boolean
  className?: string
}

function toLocalDateTimeValue(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function parseLocalDateTime(value?: string): Date | undefined {
  if (!value) return undefined
  const [datePart = '', timePart = ''] = value.split('T')
  const [year, month, day] = datePart.split('-').map((part) => Number(part))
  const [hour = 0, minute = 0] = timePart.split(':').map((part) => Number(part))
  if (!year || !month || !day) return undefined
  const parsed = new Date(year, month - 1, day, hour, minute)
  return Number.isNaN(parsed.getTime()) ? undefined : parsed
}

const HOUR_OPTIONS = Array.from({ length: 24 }, (_, i) => String(i).padStart(2, '0'))
const MINUTE_OPTIONS = Array.from({ length: 12 }, (_, i) => String(i * 5).padStart(2, '0'))

export function DateTimePicker({
  value,
  onChange,
  placeholder = 'Pick a date and time',
  disabled = false,
  className,
}: DateTimePickerProps) {
  const selected = parseLocalDateTime(value)
  const currentHour = selected ? String(selected.getHours()).padStart(2, '0') : '09'
  const currentMinute = selected ? String(Math.floor(selected.getMinutes() / 5) * 5).padStart(2, '0') : '00'

  const updateTime = (nextHour: string, nextMinute: string) => {
    const base = selected || new Date()
    const next = new Date(base)
    next.setHours(Number(nextHour), Number(nextMinute), 0, 0)
    onChange(toLocalDateTimeValue(next))
  }

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          disabled={disabled}
          className={cn('w-full justify-between text-left font-normal', !selected && 'text-muted-foreground', className)}
        >
          {selected ? format(selected, 'yyyy-MM-dd HH:mm') : placeholder}
          <CalendarIcon className="ml-2 h-4 w-4 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
        <div className="border-b p-2">
          <Calendar
            mode="single"
            selected={selected}
            onSelect={(nextDate) => {
              if (!nextDate) return
              const current = selected || new Date()
              const merged = new Date(nextDate)
              merged.setHours(current.getHours(), current.getMinutes(), 0, 0)
              onChange(toLocalDateTimeValue(merged))
            }}
            initialFocus
          />
        </div>
        <div className="grid grid-cols-2 gap-2 p-3">
          <div className="space-y-1">
            <div className="text-xs font-medium text-slate-600">Hour</div>
            <Select value={currentHour} onValueChange={(hour) => updateTime(hour, currentMinute)}>
              <SelectTrigger className="h-9">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {HOUR_OPTIONS.map((hour) => (
                  <SelectItem key={hour} value={hour}>
                    {hour}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <div className="text-xs font-medium text-slate-600">Minute</div>
            <Select value={currentMinute} onValueChange={(minute) => updateTime(currentHour, minute)}>
              <SelectTrigger className="h-9">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {MINUTE_OPTIONS.map((minute) => (
                  <SelectItem key={minute} value={minute}>
                    {minute}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  )
}
