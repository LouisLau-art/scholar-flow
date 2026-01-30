export interface Author {
  firstName: string;
  lastName: string;
  affiliation?: string;
}

export interface ArticleMetadata {
  title: string;
  authors: Author[];
  publicationDate: string; // YYYY-MM-DD
  journalTitle: string;
  doi: string;
  pdfUrl?: string;
  abstract?: string;
  volume?: string;
  issue?: string;
  firstPage?: string;
  lastPage?: string;
}

export interface MetaTag {
  name: string;
  content: string;
}

export function generateCitationMetadata(article: ArticleMetadata): MetaTag[] {
  const tags: MetaTag[] = [];

  // Required tags
  tags.push({ name: 'citation_title', content: article.title });
  tags.push({ name: 'citation_publication_date', content: article.publicationDate.replace(/-/g, '/') });
  tags.push({ name: 'citation_journal_title', content: article.journalTitle });
  tags.push({ name: 'citation_doi', content: article.doi });

  // Authors (multiple)
  article.authors.forEach(author => {
    // Highwire Press format: "Last, First" or just "Name"
    const name = `${author.lastName}, ${author.firstName}`;
    tags.push({ name: 'citation_author', content: name });
    if (author.affiliation) {
      tags.push({ name: 'citation_author_institution', content: author.affiliation });
    }
  });

  // Optional tags
  if (article.pdfUrl) {
    tags.push({ name: 'citation_pdf_url', content: article.pdfUrl });
  }
  if (article.abstract) {
    tags.push({ name: 'citation_abstract', content: article.abstract });
  }
  if (article.volume) {
    tags.push({ name: 'citation_volume', content: article.volume });
  }
  if (article.issue) {
    tags.push({ name: 'citation_issue', content: article.issue });
  }
  if (article.firstPage) {
    tags.push({ name: 'citation_firstpage', content: article.firstPage });
  }
  if (article.lastPage) {
    tags.push({ name: 'citation_lastpage', content: article.lastPage });
  }

  return tags;
}
