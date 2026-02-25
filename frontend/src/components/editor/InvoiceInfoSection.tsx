'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Pencil } from 'lucide-react'

export type InvoiceInfoView = {
  authors: string
  affiliation: string
  apcAmount: string
  fundingInfo: string
}

export function InvoiceInfoSection(props: { info: InvoiceInfoView; onEdit: () => void }) {
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle className="text-lg">Invoice Info</CardTitle>
        <Button size="sm" variant="outline" className="gap-2" onClick={props.onEdit} data-testid="invoice-edit">
          <Pencil className="h-4 w-4" />
          Edit
        </Button>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        <div className="text-muted-foreground">Authors</div>
        <div className="text-foreground whitespace-pre-wrap">{props.info.authors || '—'}</div>
        <div className="text-muted-foreground pt-2">Affiliation</div>
        <div className="text-foreground whitespace-pre-wrap">{props.info.affiliation || '—'}</div>
        <div className="text-muted-foreground pt-2">APC Amount (USD)</div>
        <div className="text-foreground">{props.info.apcAmount || '—'}</div>
        <div className="text-muted-foreground pt-2">Funding Info</div>
        <div className="text-foreground whitespace-pre-wrap">{props.info.fundingInfo || '—'}</div>
      </CardContent>
    </Card>
  )
}
