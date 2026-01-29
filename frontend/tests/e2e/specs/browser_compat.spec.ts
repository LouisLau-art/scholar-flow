import { test, expect } from '@playwright/test'

test('home page renders in supported browsers', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByText('ScholarFlow').first()).toBeVisible()
})
