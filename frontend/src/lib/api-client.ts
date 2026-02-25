import { createClient } from '@supabase/supabase-js'
import { Manuscript, ReviewReport, Invoice } from '../types'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || ''
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''

// 统一 Supabase 客户端实例
export const supabase = createClient(supabaseUrl, supabaseAnonKey)

/**
 * ScholarFlow 统一 API 封装类
 * 遵循章程：禁止在页面组件中直接书写复杂的 API 请求逻辑
 */
export const ApiClient = {
  // --- 稿件相关 ---
  async getManuscripts() {
    const { data, error } = await supabase
      .from('manuscripts')
      .select('id,title,abstract,status,created_at')
      .order('created_at', { ascending: false })
    if (error) throw error
    return data as Pick<Manuscript, 'id' | 'title' | 'abstract' | 'status' | 'created_at'>[]
  },

  async uploadManuscript(file: File, authorId: string) {
    const fileName = `${authorId}/${Date.now()}-${file.name}`
    const { data, error } = await supabase.storage
      .from('manuscripts')
      .upload(fileName, file)
    if (error) throw error
    return data.path
  },

  // --- 财务相关 ---
  async confirmPayment(invoiceId: string) {
    const { data, error } = await supabase
      .from('invoices')
      .update({ status: 'paid', confirmed_at: new Date().toISOString() })
      .eq('id', invoiceId)
    if (error) throw error
    return data
  },

  // --- 审稿相关 ---
  async submitReview(reportId: string, content: string, score: number) {
    const { data, error } = await supabase
      .from('review_reports')
      .update({ content, score, status: 'completed' })
      .eq('id', reportId)
    if (error) throw error
    return data
  },

  // --- 查重相关 ---
  async getPlagiarismStatus(manuscriptId: string) {
    const { data, error } = await supabase
      .from('plagiarism_reports')
      .select('*')
      .eq('manuscript_id', manuscriptId)
      .single()
    if (error) throw error
    return data
  },
}
