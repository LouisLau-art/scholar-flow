"use client"

import { useQuery } from "@tanstack/react-query"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { format } from "date-fns"

interface Feedback {
  id: string
  description: string
  severity: "low" | "medium" | "critical"
  url: string
  created_at: string
  status: string
}

async function getFeedback() {
  const res = await fetch("/api/v1/admin/feedback")
  if (!res.ok) throw new Error("Failed to fetch feedback")
  return res.json()
}

export function FeedbackTable() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["uat-feedback"],
    queryFn: getFeedback,
  })

  if (isLoading) return <div>Loading...</div>
  if (error) return <div>Error loading feedback</div>

  const items = data?.items || []

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Date</TableHead>
            <TableHead>Severity</TableHead>
            <TableHead>Description</TableHead>
            <TableHead>URL</TableHead>
            <TableHead>Status</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.length === 0 ? (
            <TableRow>
              <TableCell colSpan={5} className="text-center">
                No feedback reported yet.
              </TableCell>
            </TableRow>
          ) : (
            items.map((item: Feedback) => (
              <TableRow key={item.id}>
                <TableCell className="whitespace-nowrap">
                  {format(new Date(item.created_at), "MMM d, HH:mm")}
                </TableCell>
                <TableCell>
                  <Badge
                    variant={
                      item.severity === "critical"
                        ? "destructive"
                        : item.severity === "medium"
                        ? "secondary"
                        : "outline"
                    }
                  >
                    {item.severity}
                  </Badge>
                </TableCell>
                <TableCell className="max-w-[400px] truncate">
                  {item.description}
                </TableCell>
                <TableCell className="max-w-[200px] truncate text-xs text-muted-foreground">
                  {item.url}
                </TableCell>
                <TableCell>
                  <Badge variant="outline">{item.status}</Badge>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  )
}
