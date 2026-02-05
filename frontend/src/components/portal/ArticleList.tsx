import { PublicArticle } from "@/services/portal";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { format } from "date-fns";
import Link from "next/link";

interface ArticleCardProps {
  article: PublicArticle;
}

export function ArticleCard({ article }: ArticleCardProps) {
  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader>
        <div className="text-xs text-slate-500 mb-2">
          {article.published_at ? format(new Date(article.published_at), "yyyy-MM-dd") : "Recently Published"}
        </div>
        <CardTitle className="text-xl font-serif leading-tight hover:text-blue-600 transition-colors">
          <Link href={`/articles/${article.id}`}>
            {article.title}
          </Link>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-slate-600 line-clamp-3 mb-4">
          {article.abstract}
        </p>
        <div className="text-sm font-medium text-slate-900">
          {article.authors.join(", ")}
        </div>
      </CardContent>
    </Card>
  );
}

interface ArticleListProps {
  articles: PublicArticle[];
}

export function ArticleList({ articles }: ArticleListProps) {
  if (articles.length === 0) {
    return (
      <div className="text-center py-12 text-slate-500 italic">
        Recent publications will appear here.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {articles.map((article) => (
        <ArticleCard key={article.id} article={article} />
      ))}
    </div>
  );
}
