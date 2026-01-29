/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: 'http://127.0.0.1:8000/api/v1/:path*',
      },
    ]
  },
  async redirects() {
    // 处理浏览器自动探测的图标请求，避免开发环境出现 500/404 噪音。
    return [
      {
        source: '/favicon.ico',
        destination: '/favicon.svg',
        permanent: false,
      },
      {
        source: '/apple-touch-icon.png',
        destination: '/favicon.svg',
        permanent: false,
      },
    ]
  },
}

export default nextConfig
