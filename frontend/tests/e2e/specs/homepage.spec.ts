import { test, expect } from '@playwright/test'

test.describe('Homepage Portal', () => {
  test('displays banner and latest articles', async ({ page }) => {
    // Mock the latest articles API
    await page.route('**/api/v1/portal/articles/latest*', async (route) => {
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify([
          {
            id: '00000000-0000-0000-0000-000000000001',
            title: 'Mocked Published Article',
            authors: ['Mock Author'],
            abstract: 'This is a mocked abstract for testing.',
            published_at: new Date().toISOString()
          }
        ]),
      })
    })

    await page.goto('/')
    
    // Check Banner
    await expect(page.locator('h1')).toContainText('ScholarFlow Journal')
    await expect(page.getByRole('link', { name: /Submit Manuscript/i })).toBeVisible()
    
    // Check Latest Articles
    await expect(page.getByText('Latest Articles')).toBeVisible()
    await expect(page.getByText('Mocked Published Article')).toBeVisible()
    
    // Check Footer
    await expect(page.locator('footer')).toContainText('ISSN: 2073-4433')
  })
})
