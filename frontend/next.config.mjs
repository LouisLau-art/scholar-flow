/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    const backendOriginRaw =
      process.env.BACKEND_ORIGIN ||
      process.env.NEXT_PUBLIC_API_URL ||
      'http://127.0.0.1:8000'
    const backendOrigin = backendOriginRaw.replace(/\/$/, '')
    return [
      {
        source: '/api/v1/:path*',
        destination: `${backendOrigin}/api/v1/:path*`,
      },
    ]
  },
}

export default nextConfig
