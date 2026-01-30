export type DemoJournal = {
  id: string
  title: string
  slug: string
  category: string
  impact: string
  color: string
  issn?: string
  description?: string
}

export const demoJournals: DemoJournal[] = [
  { id: 'demo-1', title: 'Frontiers in Artificial Intelligence', slug: 'ai-ethics', category: 'Technology', impact: '8.4', color: 'bg-blue-600', issn: '2397-336X' },
  { id: 'demo-2', title: 'Journal of Precision Medicine', slug: 'medicine', category: 'Medical', impact: '12.1', color: 'bg-emerald-600', issn: '2471-0703' },
  { id: 'demo-3', title: 'Nature Communications (Arch)', slug: 'general-science', category: 'General Science', impact: '17.2', color: 'bg-slate-800', issn: '2041-1723' },
  { id: 'demo-4', title: 'Quantum Information Systems', slug: 'physics', category: 'Physics', impact: '9.8', color: 'bg-purple-600', issn: '1098-0121' },
  { id: 'demo-5', title: 'Global Economics & Policy', slug: 'economics', category: 'Social Science', impact: '6.5', color: 'bg-amber-600', issn: '1468-0319' },
]

