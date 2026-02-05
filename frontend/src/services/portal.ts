export interface PublicArticle {
  id: string;
  title: string;
  authors: string[];
  abstract: string;
  published_at: string;
}

export async function getLatestArticles(limit: number = 10): Promise<PublicArticle[]> {
  const response = await fetch(`/api/v1/portal/articles/latest?limit=${limit}`, {
    next: { revalidate: 3600 }, // Revalidate every hour
  });
  
  if (!response.ok) {
    throw new Error("Failed to fetch latest articles");
  }
  
  return response.json();
}
