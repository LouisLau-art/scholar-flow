'use client'

import Link from "next/link";
import { usePathname } from 'next/navigation'
import { siteConfig } from "@/config/site-config";

export function SiteFooter() {
  const pathname = usePathname() ?? '/'
  if (pathname.startsWith('/reviewer/workspace/') || pathname.startsWith('/editor/decision/')) {
    return null
  }

  return (
    <footer className="bg-slate-900 text-slate-400 py-16 border-t border-slate-800">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 grid grid-cols-2 md:grid-cols-4 gap-12 mb-12">
        <div className="col-span-2 md:col-span-1">
          <div className="font-serif text-2xl font-bold text-white mb-6">
            {siteConfig.title}
          </div>
          <p className="text-sm leading-relaxed">
            {siteConfig.description}
          </p>
          <div className="mt-4 text-xs font-mono">
            ISSN: {siteConfig.issn}
          </div>
        </div>
        <div>
          <h4 className="font-bold text-white mb-6 uppercase text-xs tracking-widest">
            Navigation
          </h4>
          <ul className="space-y-4 text-sm">
            <li>
              <Link href="/" className="hover:text-white transition-colors">Home</Link>
            </li>
            <li>
              <Link href={siteConfig.links.about} className="hover:text-white transition-colors">About the Journal</Link>
            </li>
            <li>
              <Link href={siteConfig.links.contact} className="hover:text-white transition-colors">Contact Us</Link>
            </li>
          </ul>
        </div>
        <div>
          <h4 className="font-bold text-white mb-6 uppercase text-xs tracking-widest">
            Resources
          </h4>
          <ul className="space-y-4 text-sm">
            <li className="hover:text-white cursor-pointer">Author Guidelines</li>
            <li className="hover:text-white cursor-pointer">Editorial Policies</li>
            <li className="hover:text-white cursor-pointer">Open Access Policy</li>
          </ul>
        </div>
        <div>
          <h4 className="font-bold text-white mb-6 uppercase text-xs tracking-widest">
            Submit
          </h4>
          <ul className="space-y-4 text-sm">
            <li>
              <Link href={siteConfig.links.submit} className="hover:text-white transition-colors font-semibold text-blue-400">
                Submit Your Manuscript
              </Link>
            </li>
            <li>
              <Link href="/dashboard" className="hover:text-white transition-colors">Author Dashboard</Link>
            </li>
          </ul>
        </div>
      </div>
      <div className="mx-auto max-w-7xl px-4 border-t border-slate-800 pt-8 text-center text-xs">
        <p>{siteConfig.copyright}. All rights reserved.</p>
      </div>
    </footer>
  );
}
