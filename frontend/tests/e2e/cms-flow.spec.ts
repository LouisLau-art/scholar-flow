import { test, expect } from '@playwright/test';

test.describe('CMS Content Management (US3)', () => {

  test('Admin Create Page and view at public URL', async ({ page }) => {
    // Login as Admin
    await page.goto('/login');
    await page.getByTestId('login-email').fill('admin@example.com');
    await page.getByTestId('login-password').fill('password123');
    await page.getByTestId('login-submit').click();

    await page.goto('/dashboard');
    await page.getByRole('tab', { name: /Editor/i }).click();
    await page.getByTestId('editor-tab-website').click();

    // Pages Tab
    await page.getByRole('tab', { name: 'Pages' }).click();
    
    const slug = 'about-us-e2e';
    const title = 'About Us E2E';
    
    await page.getByPlaceholder('Title').fill(title);
    // Handle Slug input if present, or assume auto-generated.
    // Usually explicit slug input exists.
    const slugInput = page.getByPlaceholder('Slug');
    if (await slugInput.isVisible()) {
        await slugInput.fill(slug);
    }
    
    await page.getByRole('button', { name: 'Create Draft' }).click();
    
    // Verify it appears in list
    const row = page.locator('tr, div').filter({ hasText: title }).last();
    await expect(row).toBeVisible();

    // Try to Publish
    // Look for a publish button or toggle in the row
    const publishBtn = row.getByRole('button', { name: 'Publish' });
    if (await publishBtn.isVisible()) {
        await publishBtn.click();
        // Wait for status change if any
        await page.waitForTimeout(500); 
    }

    // Visit public URL
    // If slug was auto-generated from title, it would be 'about-us-e2e'.
    await page.goto(`/journal/${slug}`);
    
    // Check for 404
    await expect(page.getByText('Page not found')).toBeHidden();
    
    await expect(page.getByRole('heading', { name: title })).toBeVisible();
  });

  test('Admin Update Menu', async ({ page }) => {
    // Login Admin
    await page.goto('/login');
    await page.getByTestId('login-email').fill('admin@example.com');
    await page.getByTestId('login-password').fill('password123');
    await page.getByTestId('login-submit').click();
    
    await page.goto('/dashboard');
    await page.getByRole('tab', { name: /Editor/i }).click();
    await page.getByTestId('editor-tab-website').click();
    await page.getByRole('tab', { name: 'Menu' }).click();

    // Add Item
    await page.getByRole('button', { name: 'Add Item' }).first().click();
    
    const label = 'My E2E Link';
    await page.getByPlaceholder('Label').last().fill(label);
    await page.getByPlaceholder('URL').last().fill('/journal/about-us-e2e');
    
    // Save Header Menu
    // Look for "Save" button specifically for the Header section
    await page.getByRole('button', { name: /Save.*header/i }).click();

    // Verify on Homepage
    await page.goto('/');
    await expect(page.getByRole('link', { name: label })).toBeVisible();
  });

});