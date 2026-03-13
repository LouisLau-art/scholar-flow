import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { InvoiceInfoModal, type InvoiceInfoForm } from './InvoiceInfoModal'

const form: InvoiceInfoForm = {
  authors: 'Corr Author',
  affiliation: 'Example University',
  apcAmount: '1200',
  fundingInfo: 'Grant 1',
}

describe('InvoiceInfoModal', () => {
  it('renders save and save-send actions when invoice email is available', () => {
    const onSave = vi.fn()
    const onSaveAndSend = vi.fn()

    render(
      <InvoiceInfoModal
        open
        onOpenChange={vi.fn()}
        form={form}
        onChange={vi.fn()}
        onSave={onSave}
        onSaveAndSend={onSaveAndSend}
        canSendEmail
        invoiceNumber="INV-2026-001"
      />
    )

    expect(screen.getByText('Invoice email will be sent with PDF attachment once the invoice info is confirmed.')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    expect(onSave).toHaveBeenCalledTimes(1)

    fireEvent.click(screen.getByRole('button', { name: 'Save & Send Invoice Email' }))
    expect(onSaveAndSend).toHaveBeenCalledTimes(1)
  })

  it('locks fields and actions while invoice email is sending', () => {
    render(
      <InvoiceInfoModal
        open
        onOpenChange={vi.fn()}
        form={form}
        onChange={vi.fn()}
        onSave={vi.fn()}
        onSaveAndSend={vi.fn()}
        canSendEmail
        invoiceNumber="INV-2026-001"
        sendingEmail
      />
    )

    expect(screen.getByDisplayValue('Corr Author')).toBeDisabled()
    expect(screen.getByDisplayValue('Example University')).toBeDisabled()
    expect(screen.getByDisplayValue('1200')).toBeDisabled()
    expect(screen.getByDisplayValue('Grant 1')).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Save' })).toBeDisabled()
    expect(screen.getByRole('button', { name: /Save & Send Invoice Email/i })).toBeDisabled()
  })
})
