import { readFile } from 'node:fs/promises'
import { join } from 'node:path'

export async function GET() {
  // 路由处理器：避免浏览器默认请求 /favicon.ico 时出现 500/404 噪音。
  // 优先使用 public/ 下的产物，便于用 ImageMagick 一次性生成多尺寸图标。
  const iconPath = join(process.cwd(), 'public', 'favicon.ico')
  const buf = await readFile(iconPath)
  return new Response(buf, {
    headers: {
      'Content-Type': 'image/x-icon',
      'Cache-Control': 'public, max-age=0, must-revalidate',
    },
  })
}

