import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { toast } from 'sonner'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function showErrorToast(error: unknown, fallbackMessage = 'Operation failed', options?: { id?: string | number }) {
  console.error(error)
  const message = error instanceof Error ? error.message : (typeof error === 'string' ? error : fallbackMessage)
  toast.error(message, options)
}