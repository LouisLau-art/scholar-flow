import { test, expect } from '@playwright/test';

test.describe('Editor Critical User Journey (US2)', () => {

  test('Editor Login & Dashboard Load', async ({ page }) => {
    await page.goto('/login');
    await page.getByTestId('login-email').fill('editor@example.com');
    await page.getByTestId('login-password').fill('password123');
    await page.getByTestId('login-submit').click();
    
    await expect(page).toHaveURL(/.*\/dashboard/);
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
    
    await page.getByRole('tab', { name: /Editor/i }).click();
    await expect(page.getByText('Editor Command Center')).toBeVisible();
  });

  test('Assign Reviewer', async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.getByTestId('login-email').fill('editor@example.com');
    await page.getByTestId('login-password').fill('password123');
    await page.getByTestId('login-submit').click();

    await page.goto('/dashboard');
    await page.getByRole('tab', { name: /Editor/i }).click();

    // Look for "The Impact of Automated Testing" (Submitted status)
    // We look for a container (row or card) containing the title.
    const card = page.locator('div, tr').filter({ hasText: 'The Impact of Automated Testing' }).last();
    await expect(card).toBeVisible();

    // Click "Assign Reviewers" within that card/row
    await card.getByRole('button', { name: 'Assign Reviewers' }).click();
    
    // Modal opens
    await expect(page.getByTestId('reviewer-modal')).toBeVisible();
    
    // Select Reviewer 2 (333...)
    // Ensure the list is loaded.
    await expect(page.getByTestId('reviewer-list')).toBeVisible();
    
    // Click the item. 
    await page.getByTestId('reviewer-item-33333333-3333-4333-a333-333333333333').click();
    
    // Confirm assignment
    await page.getByTestId('reviewer-assign').click();

    // Verify success
    // Toast might appear
    // Or check if the button changed to "Reviewers Assigned" or similar, or card moved.
    // For now, check for a generic success indication or absence of the modal.
    await expect(page.getByTestId('reviewer-modal')).toBeHidden();
    
    // Ideally check if the status updated on the card
    // await expect(card).toContainText('Under Review'); // or similar
  });

  test('Submit Decision (Accept)', async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.getByTestId('login-email').fill('editor@example.com');
    await page.getByTestId('login-password').fill('password123');
    await page.getByTestId('login-submit').click();

    await page.goto('/dashboard');
    await page.getByRole('tab', { name: /Editor/i }).click();

    // Find "Ready for Decision"
    const card = page.locator('div, tr').filter({ hasText: 'Ready for Decision' }).last();
    await expect(card).toBeVisible();

    // Click "Make Decision"
    await card.getByRole('button', { name: 'Make Decision' }).click();
    
    // Modal opens
    await expect(page.getByText('Final Decision')).toBeVisible();

    // Select Accept
    // We assume there's a visible text "Accept for Publication" to click, or a radio/button.
    await page.getByText('Accept for Publication').click();
    
    // Submit
    await page.getByRole('button', { name: 'Submit Decision' }).click();

    // Verify
    await expect(page.getByText('Decision Submitted')).toBeVisible();
    
    // Verify it moved to Published or is no longer in Pending Decision
    await expect(card).not.toBeVisible(); 
    // (Assuming it moves to another list/tab)
  });

});