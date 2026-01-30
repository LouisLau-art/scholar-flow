import { describe, it, expect } from 'vitest';
import { generateCitationMetadata } from '../../src/lib/metadata/citation';

describe('generateCitationMetadata', () => {
  it('should generate required meta tags', () => {
    const article = {
      title: 'Test Article',
      authors: [{ firstName: 'John', lastName: 'Doe' }],
      publicationDate: '2024-01-01',
      journalTitle: 'Test Journal',
      doi: '10.12345/sf.2024.00001',
      pdfUrl: 'https://example.com/pdf'
    };

    const tags = generateCitationMetadata(article);
    
    expect(tags).toContainEqual({ name: 'citation_title', content: 'Test Article' });
    expect(tags).toContainEqual({ name: 'citation_author', content: 'Doe, John' });
    expect(tags).toContainEqual({ name: 'citation_publication_date', content: '2024/01/01' });
    expect(tags).toContainEqual({ name: 'citation_journal_title', content: 'Test Journal' });
    expect(tags).toContainEqual({ name: 'citation_doi', content: '10.12345/sf.2024.00001' });
    expect(tags).toContainEqual({ name: 'citation_pdf_url', content: 'https://example.com/pdf' });
  });

  it('should handle multiple authors', () => {
    const article = {
      title: 'Test Article',
      authors: [
        { firstName: 'John', lastName: 'Doe' },
        { firstName: 'Jane', lastName: 'Smith' }
      ],
      publicationDate: '2024-01-01',
      journalTitle: 'Test Journal',
      doi: '10.12345/sf.2024.00001'
    };

    const tags = generateCitationMetadata(article);
    
    expect(tags.filter(t => t.name === 'citation_author')).toHaveLength(2);
    expect(tags).toContainEqual({ name: 'citation_author', content: 'Doe, John' });
    expect(tags).toContainEqual({ name: 'citation_author', content: 'Smith, Jane' });
  });
});
