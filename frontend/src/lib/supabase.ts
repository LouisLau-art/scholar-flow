import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || ''
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''

// === 全局 Supabase 客户端 (原生版) ===
// 中文注释:
// 1. 放弃不稳定的 auth-helpers，使用原生 createClient。
// 2. 确保在 Client Components 中能够稳定工作。
export const supabase = createClient(supabaseUrl, supabaseAnonKey)
