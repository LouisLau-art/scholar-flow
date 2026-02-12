import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import CmsPagesPanel from '@/components/cms/CmsPagesPanel'

vi.mock('@/components/cms/TiptapEditor', () => ({
  default: ({ value, onChange }: any) => (
    <textarea
      data-testid="mock-editor"
      value={value}
      onChange={(e) => onChange(e.target.value)}
    />
  ),
}))

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

const listCmsPages = vi.fn()
const createCmsPage = vi.fn()
const updateCmsPage = vi.fn()
const uploadCmsImage = vi.fn()

vi.mock('@/services/cms', () => ({
  listCmsPages: (...args: any[]) => listCmsPages(...args),
  createCmsPage: (...args: any[]) => createCmsPage(...args),
  updateCmsPage: (...args: any[]) => updateCmsPage(...args),
  uploadCmsImage: (...args: any[]) => uploadCmsImage(...args),
}))

describe('CmsPagesPanel', () => {
  beforeEach(() => {
    listCmsPages.mockResolvedValue([
      { id: '1', slug: 'about', title: 'About', content: '<p>Hello</p>', is_published: false },
    ])
    createCmsPage.mockResolvedValue({ id: '2', slug: 'contact', title: 'Contact', content: '<p></p>', is_published: false })
    updateCmsPage.mockResolvedValue({ id: '1', slug: 'about', title: 'About', content: 'x', is_published: true })
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('loads pages and allows save', async () => {
    render(<CmsPagesPanel />)

    expect(await screen.findByText('Pages')).toBeInTheDocument()
    expect(listCmsPages).toHaveBeenCalled()

    // 等待选中页回填完成，避免 useEffect 后续重置发布态造成测试抖动。
    expect(await screen.findByDisplayValue('About')).toBeInTheDocument()
    const checkbox = await screen.findByRole('checkbox')
    expect(checkbox).not.toBeChecked()
    fireEvent.click(checkbox)
    expect(checkbox).toBeChecked()

    const saveButton = await screen.findByRole('button', { name: 'Save' })
    fireEvent.click(saveButton)

    await waitFor(() => {
      expect(updateCmsPage).toHaveBeenCalledWith('about', expect.objectContaining({ is_published: true }))
    })
  })
})
