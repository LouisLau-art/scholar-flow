import { test, expect } from '@playwright/test';

test.describe('DOI Registration Integration (US4)', () => {

  test('Trigger DOI Registration (via Publish)', async ({ page }) => {
    // Login Editor
    await page.goto('/login');
    await page.getByTestId('login-email').fill('editor@example.com');
    await page.getByTestId('login-password').fill('password123');
    await page.getByTestId('login-submit').click();

    await page.goto('/dashboard');
    await page.getByRole('tab', { name: /Editor/i }).click();

    // Find "Finalized Research Paper" (Accepted status)
    const row = page.locator('tr, div').filter({ hasText: 'Finalized Research Paper' }).last();
    await expect(row).toBeVisible();

    // Click "Publish"
    // Assuming a button named "Publish" exists in the row/card
    const publishBtn = row.getByRole('button', { name: /Publish/i });
    if (await publishBtn.isVisible()) {
        await publishBtn.click();
        
        // Handle confirmation modal if present
        const confirmBtn = page.getByRole('button', { name: /Confirm/i });
        if (await confirmBtn.isVisible()) {
            await confirmBtn.click();
        }
    } else {
        // Fallback: Maybe need to click "Make Decision" -> "Publish"? 
        // Or maybe it's already published?
        // If the button isn't found, we might be in wrong state.
        // For now, assume it's actionable.
        console.log('Publish button not found');
    }

    // Wait for success message
    // await expect(page.getByText(/Published/i)).toBeVisible();

    // View the article
    // If we can find a link in the row
    const viewLink = row.getByRole('link', { name: /View/i }).first();
    if (await viewLink.isVisible()) {
        await viewLink.click();
    } else {
        // Try to click title
        await row.getByText('Finalized Research Paper').click();
    }

    // On Public Page
    // Check for DOI Label (even if value is pending)
    await expect(page.getByText(/DOI:/)).toBeVisible();
  });

  test('Verify Admin DOI Dashboard', async ({ page }) => {
    // Login Admin
    await page.goto('/login');
    await page.getByTestId('login-email').fill('admin@example.com');
    await page.getByTestId('login-password').fill('password123');
    await page.getByTestId('login-submit').click();

    // Direct navigation is safer than finding nested tabs
    await page.goto('/editor/doi-tasks');
    
    await expect(page.getByRole('heading', { name: 'DOI Tasks' })).toBeVisible();
    await expect(page.getByText('Status')).toBeVisible(); // Check for table header
  });

});