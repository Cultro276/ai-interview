import { test, expect } from '@playwright/test';

test.describe('Interview flow (smoke)', () => {
  test('renders consent and navigates to permissions', async ({ page }) => {
    // Mock token verify and consent to avoid backend dependency
    await page.route('**/api/v1/tokens/verify**', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
    });
    await page.route('**/api/v1/tokens/consent**', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
    });
    // Start with a tokenized route (dev: use a dummy token that passes verify in local env)
    const token = process.env.E2E_TOKEN || 'dummy-token';
    await page.goto(`/interview/${token}`);

    // Should show loading/consent content then proceed after clicking
    await page.waitForTimeout(500);
    await expect(page.locator('text=KVKK Aydınlatma Metni')).toBeVisible({ timeout: 10_000 });

    // Accept consent
    await page.getByRole('checkbox').first().check();
    await page.getByRole('button', { name: 'Devam Et' }).click();

    // Permissions step should appear
    await expect(page.locator('text=Kamera ve mikrofon izinleri isteniyor…')).toBeVisible({ timeout: 10_000 });
  });
});


