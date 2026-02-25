'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Pencil } from 'lucide-react'
import { Table, TableBody, TableCell, TableRow } from '@/components/ui/table'

export type InvoiceInfoPanelView = {
  authors: string
  affiliation: string
  apcAmount: string
  fundingInfo: string
}

export function InvoiceInfoPanel({ info, onEdit }: { info: InvoiceInfoPanelView; onEdit: () => void }) {
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle className="text-lg">Invoice Info</CardTitle>
        <Button size="sm" variant="outline" className="gap-2" onClick={onEdit} data-testid="invoice-edit">
          <Pencil className="h-4 w-4" />
          Edit
        </Button>
      </CardHeader>
      <CardContent className="pt-0">
        <Table>
          <TableBody>
            <TableRow>
              <TableCell className="w-44 text-muted-foreground">Authors (Billable)</TableCell>
              <TableCell className="whitespace-pre-wrap">{info.authors || '—'}</TableCell>
            </TableRow>
            <TableRow>
              <TableCell className="w-44 text-muted-foreground">Affiliation</TableCell>
              <TableCell className="whitespace-pre-wrap">{info.affiliation || '—'}</TableCell>
            </TableRow>
            <TableRow>
              <TableCell className="w-44 text-muted-foreground">APC Amount (USD)</TableCell>
              <TableCell>{info.apcAmount || '—'}</TableCell>
            </TableRow>
            <TableRow>
              <TableCell className="w-44 text-muted-foreground">Funding</TableCell>
              <TableCell className="whitespace-pre-wrap">{info.fundingInfo || '—'}</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
