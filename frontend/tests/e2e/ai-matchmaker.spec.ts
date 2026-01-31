import { test, expect } from '@playwright/test';

test.describe('AI Matchmaker Integration (US5)', () => {

  test('Open Assignment Modal & Load Suggestions', async ({ page }) => {
    // Login Editor
    await page.goto('/login');
    await page.getByTestId('login-email').fill('editor@example.com');
    await page.getByTestId('login-password').fill('password123');
    await page.getByTestId('login-submit').click();

    await page.goto('/dashboard');
    await page.getByRole('tab', { name: /Editor/i }).click();

    // Find "The Impact of Automated Testing"
    // Use last() to pick one if duplicates exist (though seed should be unique)
    const row = page.locator('tr, div').filter({ hasText: 'The Impact of Automated Testing' }).last();
    await expect(row).toBeVisible();

    // Open Assign Modal
    await row.getByRole('button', { name: 'Assign Reviewers' }).click();
    await expect(page.getByTestId('reviewer-modal')).toBeVisible();

    // Trigger AI Matchmaking
    const analyzeBtn = page.getByTestId('ai-analyze');
    if (await analyzeBtn.isVisible()) {
        await analyzeBtn.click();
    } else {
        const recTab = page.getByText('Recommended');
        if (await recTab.isVisible()) {
            await recTab.click();
        }
    }

    // Verify Result (Success or graceful failure)
    await expect(async () => {
        const hasScore = await page.getByText(/Match Score/i).isVisible();
        const hasNoData = await page.getByText(/No recommendations/i).isVisible();
        const hasInsufficient = await page.getByText(/Insufficient data/i).isVisible();
        
        if (hasScore || hasNoData || hasInsufficient) return true;
        
        // Also check if list items appeared (fallback)
        const items = await page.getByTestId('ai-recommendation-item').count();
        if (items > 0) return true;

        throw new Error('AI Matchmaker UI state not recognized (No scores, no empty message)');
    }).toPass({ timeout: 10000 }); // Give AI some time
  });

});