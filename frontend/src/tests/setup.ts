import '@testing-library/jest-dom/vitest'
import { vi } from 'vitest'

// === 全局 Mock 配置 ===
// 中文注释:
// 1. Mock Next.js 路由，防止在测试环境中报错。
// 2. Mock Supabase 客户端。

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    refresh: vi.fn(),
  }),
  useSearchParams: () => ({
    get: vi.fn(),
  }),
  useParams: () => ({
    id: 'test-id',
    slug: 'test-slug',
  }),
}))

vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      signInWithPassword: vi.fn(),
      signUp: vi.fn(),
    }
  }
}))
