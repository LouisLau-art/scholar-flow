import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import SubmissionForm from '@/components/SubmissionForm'
import { vi, describe, it, expect } from 'vitest'

describe('SubmissionForm Component', () => {
  /**
   * 验证投稿表单核心交互
   * 中文注释:
   * 1. 测试按钮初始状态 (未填写 Title 时应禁用)。
   * 2. 模拟用户输入标题并验证按钮启用。
   */
  
  it('disables submit button if title is empty', () => {
    render(<SubmissionForm />)
    const submitBtn = screen.getByRole('button', { name: /finalize submission/i })
    expect(submitBtn).toBeDisabled()
  })

  it('enables submit button when title is provided', async () => {
    render(<SubmissionForm />)
    const titleInput = screen.getByPlaceholderText(/parsed title will appear here/i)
    
    fireEvent.change(titleInput, { target: { value: 'New Scholarly Work' } })
    
    const submitBtn = screen.getByRole('button', { name: /finalize submission/i })
    expect(submitBtn).not.toBeDisabled()
  })
})
