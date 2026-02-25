export async function GET() {
  // 简单的 SVG favicon，避免 /favicon.ico 在开发环境报错噪音。
  const svg = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="rgb(37, 99, 235)"/>
      <stop offset="1" stop-color="rgb(15, 23, 42)"/>
    </linearGradient>
  </defs>
  <rect x="4" y="4" width="56" height="56" rx="14" fill="url(#g)"/>
  <text x="32" y="40" text-anchor="middle" font-family="ui-sans-serif, system-ui, -apple-system, Segoe UI" font-size="26" font-weight="700" fill="white">SF</text>
</svg>`

  return new Response(svg, {
    headers: {
      'Content-Type': 'image/svg+xml; charset=utf-8',
      'Cache-Control': 'public, max-age=0, must-revalidate',
    },
  })
}
