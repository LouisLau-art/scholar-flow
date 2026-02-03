import { test, expect } from '@playwright/test';

// Skip these tests if we are not in staging mode locally, 
// OR mock the environment in the test setup.
// Since Playwright runs against a build, we assume the target URL is running.
// We can check if the banner is present.

test.describe('UAT Staging Environment', () => {
  test('Banner should be visible in Staging environment', async ({ page }) => {
    // Navigate to homepage
    await page.goto('/');

    // Check for UAT Banner
    // Note: This test assumes the app under test IS running in Staging mode.
    // If we run this against production, this test SHOULD fail (as per requirement).
    // However, for CI/CD, we might want to conditionally run it.
    
    // For now, we assert it's visible based on the "Staging" premise of this spec.
    const banner = page.getByText('Current Environment: UAT Staging (Not for Production)');
    
    // We use a conditional check here to make the test useful in both envs?
    // No, the requirement says verify presence in Staging and absence in Prod.
    // We'll assume the test runner knows which env it's hitting.
    // Let's assert visibility.
    await expect(banner).toBeVisible();
  });

  test('Feedback Widget should be visible in Staging', async ({ page }) => {
    await page.goto('/');
    
    const widgetButton = page.getByRole('button', { name: /report issue/i });
    await expect(widgetButton).toBeVisible();
  });

  test('Feedback Widget opens dialog on click', async ({ page }) => {
    await page.goto('/');
    
    const widgetButton = page.getByRole('button', { name: /report issue/i });
    await widgetButton.click();
    
    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();
    await expect(page.getByText('Report an Issue')).toBeVisible();
  });
});
