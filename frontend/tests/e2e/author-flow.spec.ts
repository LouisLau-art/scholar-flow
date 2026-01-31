import { test, expect } from '@playwright/test';

test.describe('Author Critical User Journey (US1)', () => {

  test('Author Registration', async ({ page }) => {
    const uniqueId = Date.now();
    const newAuthorEmail = `author_${uniqueId}@example.com`;
    const newAuthorPassword = 'password123';

    await page.goto('/signup');
    await page.getByTestId('signup-email').fill(newAuthorEmail);
    await page.getByTestId('signup-password').fill(newAuthorPassword);
    
    // Handle potential confirm password field if it exists (defensive)
    const confirmPass = page.getByTestId('signup-password-confirm');
    if (await confirmPass.isVisible()) {
        await confirmPass.fill(newAuthorPassword);
    }

    await page.getByTestId('signup-submit').click();

    // We expect either a redirect to dashboard OR a "Check your email" message.
    // In a development environment without email confirmation, it should auto-login.
    // If it requires confirmation, we check for success message.
    await expect(async () => {
        const url = page.url();
        const successMsg = await page.getByText('Check your email').isVisible();
        if (url.includes('/dashboard') || successMsg) {
            return true;
        }
        throw new Error('Neither dashboard redirect nor check email message observed');
    }).toPass();
  });

  test('Author Login', async ({ page }) => {
    await page.goto('/login');
    await page.getByTestId('login-email').fill('author@example.com');
    await page.getByTestId('login-password').fill('password123');
    await page.getByTestId('login-submit').click();
    
    await expect(page).toHaveURL(/.*\/dashboard/);
    await expect(page.getByRole('heading', { name: 'My Submissions' })).toBeVisible();
  });

  test('Submit Manuscript', async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.getByTestId('login-email').fill('author@example.com');
    await page.getByTestId('login-password').fill('password123');
    await page.getByTestId('login-submit').click();
    await expect(page).toHaveURL(/.*\/dashboard/);

    // Go to submission
    await page.goto('/submit');
    
    // File Upload (Dummy PDF)
    const pdfBuffer = Buffer.from('%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF');
    // Note: ensure the input selector matches the app. 
    // Usually it's input[type="file"] or finding by testid if the input itself has it.
    // The SubmissionPage helper used '[data-testid="submission-file"]'.
    // If the input is hidden (e.g. styled dropzone), we might need to point to the input specifically.
    // We'll try the generic file input locator if testid fails or specific strategy.
    
    // Assuming the file input is identifiable. 
    // If Shadcn/React Dropzone is used, the input is often hidden.
    // Playwright handles hidden inputs with setInputFiles.
    
    await page.setInputFiles('input[type="file"]', {
      name: 'test_manuscript.pdf',
      mimeType: 'application/pdf',
      buffer: pdfBuffer,
    });

    await page.getByTestId('submission-title').fill('E2E Test Manuscript ' + Date.now());
    await page.getByTestId('submission-abstract').fill('This is an abstract for the E2E regression test.');

    // Submit
    await page.getByTestId('submission-finalize').click();

    // Verify
    await expect(page).toHaveURL(/.*\/dashboard/);
    await expect(page.getByText('E2E Test Manuscript')).toBeVisible();
    await expect(page.getByText('Submitted')).toBeVisible();
  });

});