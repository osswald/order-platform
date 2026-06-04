import { expect, test } from '@playwright/test'

const adminEmail = process.env.CLOUD_ADMIN_EMAIL || 'admin@vendiqo.local'
const adminPassword = process.env.CLOUD_ADMIN_PASSWORD || 'admin123'

test('admin can log in and reach the dashboard', async ({ page }) => {
  await page.goto('/login')
  await expect(page.getByRole('heading', { name: 'Vendiqo' })).toBeVisible()

  await page.locator('#email').fill(adminEmail)
  await page.locator('#password').fill(adminPassword)
  await page.getByRole('button', { name: 'Anmelden' }).click()

  await expect(page.getByText('Anmeldung erfolgreich!')).toBeVisible()
  await page.waitForURL('**/dashboard**', { timeout: 20_000 })
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
})
