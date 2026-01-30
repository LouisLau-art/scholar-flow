import { readFile } from 'node:fs/promises'
import { join } from 'node:path'

export async function GET() {
  // iOS/Safari 会探测 /apple-touch-icon.png。
  const iconPath = join(process.cwd(), 'public', 'apple-touch-icon.png')
  const buf = await readFile(iconPath)
  return new Response(buf, {
    headers: {
      'Content-Type': 'image/png',
      'Cache-Control': 'public, max-age=0, must-revalidate',
    },
  })
}

