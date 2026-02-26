import { test, expect } from '@playwright/test'

test.describe('Homepage Portal', () => {
  test('displays banner and latest articles', async ({ page }) => {
    await page.goto('/')
    
    // Check Banner
    await expect(page.locator('h1')).toContainText('ScholarFlow Journal')
    await expect(page.getByRole('link', { name: /Submit Manuscript/i })).toBeVisible()
    
    // Check Latest Articles block (homepage now uses server-side data/fallback)
    const latestSection = page.locator('section').filter({ hasText: 'Latest Articles from ScholarFlow Journal' }).first()
    await expect(latestSection).toBeVisible()
    await expect(latestSection.locator('a').first()).toBeVisible()
    
    // Check Footer
    await expect(page.locator('footer')).toContainText('ISSN: 2073-4433')
  })
})
