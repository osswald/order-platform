import { expect, test } from '@playwright/test'

test('waiter can add an article and see the cart total', async ({ page }) => {
  await page.goto('/events')
  await expect(page.getByRole('heading', { name: 'Events' })).toBeVisible()

  await page.getByRole('button', { name: /E2E Test/ }).click()
  await expect(page.getByRole('heading', { name: 'Modus wählen' })).toBeVisible()
  await page.getByRole('button', { name: 'Kellner' }).click()
  await expect(page.getByRole('heading', { name: 'Kellner' })).toBeVisible()

  await page.locator('input.input').fill('1234')
  await page.getByRole('button', { name: 'Anmelden' }).click()
  await expect(page.getByRole('heading', { name: 'Kellner' })).toBeVisible()
  await expect(page.getByText('Anna')).toBeVisible()

  await page.getByRole('button', { name: 'Neue Bestellung' }).click()
  await page.getByRole('button', { name: '5', exact: true }).click()
  await page.getByRole('button', { name: 'OK' }).click()

  await page.getByRole('button', { name: 'Bier' }).click()
  await expect(page.locator('.header-center')).toContainText('5.00')
  await expect(page.locator('.header-center')).toContainText('1')
})
