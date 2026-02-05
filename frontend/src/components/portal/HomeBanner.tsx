import Link from "next/link";
import { siteConfig } from "@/config/site-config";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export function HomeBanner() {
  return (
    <section className="bg-slate-900 text-white py-20 px-4">
      <div className="max-w-6xl mx-auto flex flex-col items-center text-center">
        <h1 className="text-4xl md:text-6xl font-serif mb-6">{siteConfig.title}</h1>
        <p className="text-xl text-slate-300 max-w-2xl mb-8">
          {siteConfig.description}
        </p>
        <div className="flex gap-4 mb-10">
          <Badge variant="outline" className="text-white border-white/20">
            ISSN: {siteConfig.issn}
          </Badge>
          <Badge variant="secondary" className="bg-blue-600 text-white hover:bg-blue-700 border-none">
            Impact Factor: {siteConfig.impact_factor}
          </Badge>
        </div>
        <Button size="lg" asChild className="px-10 h-12 text-lg">
          <Link href={siteConfig.links.submit}>Submit Manuscript</Link>
        </Button>
      </div>
    </section>
  );
}
