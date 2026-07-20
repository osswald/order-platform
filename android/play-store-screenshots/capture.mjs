#!/usr/bin/env node
/**
 * Capture Google Play tablet screenshots from the live Play Review demo.
 *
 * Usage:
 *   cd android/play-store-screenshots && npm ci && npx playwright install chromium
 *   node capture.mjs
 *
 * Env:
 *   PLAY_REVIEW_URL  base URL (default https://play-review.demo.vendiqo.ch)
 *   TABLE_NUMBER     table for order/pay shots (default 12)
 *   HEADED           set to 1 to show the browser
 */
import { chromium } from 'playwright'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import {
  EXPECTED_VIEWPORTS,
  SCREENSHOT_SLUGS,
  pngDimensions,
  validatePlayTabletSize,
} from './pngMeta.mjs'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const BASE = (process.env.PLAY_REVIEW_URL || 'https://play-review.demo.vendiqo.ch').replace(/\/$/, '')
const TABLE = String(process.env.TABLE_NUMBER || '12')
const HEADED = process.env.HEADED === '1'
const EVENT_NAME = 'Play Review Demo'
const WAITER_NAME = 'Martina Meier'
const PIN = '0000'

/** @type {Record<string, string>} */
const CAPTURE_KEYS = {
  hub: '01-hub',
  events: '02-events',
  login: '03-login',
  keypad: '04-table-keypad',
  orderEmpty: '05-order-empty',
  orderFilled: '06-order-filled',
  openTables: '07-open-tables',
  payTable: '08-pay-table',
}

async function dismissShiftDialog(page) {
  const start = page.getByRole('dialog').getByRole('button', { name: /^Start$/ })
  try {
    await start.waitFor({ state: 'visible', timeout: 2500 })
    await start.click()
    await page.getByRole('dialog').waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {})
  } catch {
    // No shift dialog this session
  }
}

async function waitAppReady(page) {
  await page.waitForLoadState('networkidle').catch(() => {})
  await page.waitForTimeout(400)
}

/**
 * Force tablet (Android-like) chrome: hide hosted-demo receipts rail so
 * order screen uses landscape cart | grid split at >=768px.
 */
async function installDemoOverrides(page) {
  await page.route('**/v1/setup/status', async (route) => {
    const res = await route.fetch()
    const body = await res.json()
    body.emulated_printer = false
    await route.fulfill({
      status: res.status(),
      contentType: 'application/json',
      body: JSON.stringify(body),
    })
  })
}

/**
 * @param {import('playwright').Page} page
 * @param {string} outPath
 */
async function shot(page, outPath) {
  await waitAppReady(page)
  // Dismiss toasts if any
  await page.locator('.toast').waitFor({ state: 'hidden', timeout: 1500 }).catch(() => {})
  await page.screenshot({ path: outPath, fullPage: false, type: 'png' })
}

/**
 * @param {import('playwright').Page} page
 * @param {string} label
 */
async function clickCellByLabel(page, label) {
  const cell = page.locator('.grid .cell', { hasText: label }).first()
  await cell.waitFor({ state: 'visible', timeout: 10000 })
  await cell.click()
  // Optional multi-article / additions sheets
  const sheetItem = page.locator('.sheet button, .sheet .picker-row, .article-picker button').first()
  const additionsConfirm = page.getByRole('button', { name: /Übernehmen|OK|Hinzufügen|Bestätigen/i })
  await page.waitForTimeout(350)
  if (await sheetItem.isVisible().catch(() => false)) {
    await sheetItem.click()
    await page.waitForTimeout(300)
  }
  if (await additionsConfirm.isVisible().catch(() => false)) {
    await additionsConfirm.click()
    await page.waitForTimeout(300)
  }
}

/**
 * @param {import('playwright').Browser} browser
 * @param {'7in' | '10in'} sizeKey
 */
async function captureSize(browser, sizeKey) {
  const vp = EXPECTED_VIEWPORTS[sizeKey]
  const context = await browser.newContext({
    viewport: vp,
    deviceScaleFactor: 1,
    locale: 'de-CH',
    colorScheme: 'light',
  })
  const page = await context.newPage()
  await installDemoOverrides(page)

  /** @type {Record<string, string>} */
  const files = {}

  const save = async (key) => {
    const slug = CAPTURE_KEYS[key]
    const name = `${sizeKey}-${slug}.png`
    const outPath = path.join(__dirname, name)
    await shot(page, outPath)
    files[key] = outPath
    console.log(`  wrote ${name}`)
  }

  // --- Events ---
  await page.goto(`${BASE}/#/events`, { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: new RegExp(EVENT_NAME) }).waitFor({ state: 'visible', timeout: 30000 })
  await save('events')

  await page.getByRole('button', { name: new RegExp(EVENT_NAME) }).click()
  await page.getByRole('button', { name: 'Kellner' }).waitFor({ state: 'visible', timeout: 15000 })
  await page.getByRole('button', { name: 'Kellner' }).click()

  // --- Login ---
  await page.getByRole('button', { name: /Kellner wählen|Martina|Martin/ }).waitFor({ state: 'visible', timeout: 15000 })
  // Open picker if needed and select Martina
  const picker = page.locator('.waiter-picker')
  const selectedName = await page.locator('.waiter-picker-name').textContent().catch(() => '')
  if (!String(selectedName || '').includes(WAITER_NAME)) {
    await picker.click()
    await page.locator('.waiter-row', { hasText: WAITER_NAME }).click()
  }
  await page.locator('input.input').fill(PIN)
  await save('login')

  await page.getByRole('button', { name: 'Anmelden' }).click()
  await dismissShiftDialog(page)
  await page.getByRole('button', { name: 'Neue Bestellung' }).waitFor({ state: 'visible', timeout: 20000 })
  await save('hub')

  // --- Table keypad ---
  await page.getByRole('button', { name: 'Neue Bestellung' }).click()
  await page.locator('.table-keypad').waitFor({ state: 'visible', timeout: 10000 })
  for (const d of TABLE.split('')) {
    await page.locator('.table-keypad .key', { hasText: new RegExp(`^${d}$`) }).click()
  }
  await save('keypad')
  await page.locator('.table-keypad').getByRole('button', { name: 'OK' }).click()

  // --- Order empty ---
  await page.locator('.order-screen').waitFor({ state: 'visible', timeout: 15000 })
  await page.locator('.grid .cell').first().waitFor({ state: 'visible', timeout: 15000 })
  await save('orderEmpty')

  // --- Order filled ---
  await clickCellByLabel(page, 'Crèmeschnitte')
  await clickCellByLabel(page, 'Schwarzwälder')
  await clickCellByLabel(page, 'Kaffee')
  await page.locator('.cart-lines .cart-line, .cart-line').first().waitFor({ state: 'visible', timeout: 10000 })
  await save('orderFilled')

  await page.getByRole('button', { name: /FERTIG/ }).click()
  // After submit, expect hub (or stay on order briefly)
  await page.getByRole('button', { name: 'Offene Tische' }).waitFor({ state: 'visible', timeout: 20000 })
  await dismissShiftDialog(page)

  // --- Open tables ---
  await page.getByRole('button', { name: 'Offene Tische' }).click()
  await page.getByRole('heading', { name: 'Offene Tische' }).waitFor({ state: 'visible', timeout: 15000 })
  await page.locator('.table-row, .card').first().waitFor({ state: 'visible', timeout: 15000 })
  await save('openTables')

  // Prefer the table we just ordered
  const tableBtn = page.locator('.table-row', { hasText: `Tisch ${TABLE}` })
  if (await tableBtn.isVisible().catch(() => false)) {
    await tableBtn.click()
  } else {
    await page.locator('.table-row').first().click()
  }

  // --- Pay / settle ---
  await page.locator('.split-pay-screen, .split-body').first().waitFor({ state: 'visible', timeout: 20000 })
  await save('payTable')

  await context.close()

  // Validate
  for (const slug of SCREENSHOT_SLUGS) {
    const file = path.join(__dirname, `${sizeKey}-${slug}.png`)
    if (!fs.existsSync(file)) throw new Error(`Missing ${file}`)
    const dim = pngDimensions(fs.readFileSync(file))
    const check = validatePlayTabletSize(sizeKey, dim.width, dim.height)
    if (!check.ok) throw new Error(`${file}: ${check.reason}`)
    if (dim.width !== vp.width || dim.height !== vp.height) {
      throw new Error(`${file}: expected ${vp.width}x${vp.height}, got ${dim.width}x${dim.height}`)
    }
  }

  return files
}

async function main() {
  console.log(`Capturing from ${BASE}`)
  const browser = await chromium.launch({ headless: !HEADED })
  try {
    for (const sizeKey of /** @type {const} */ (['10in', '7in'])) {
      console.log(`\n${sizeKey} ${EXPECTED_VIEWPORTS[sizeKey].width}x${EXPECTED_VIEWPORTS[sizeKey].height}`)
      await captureSize(browser, sizeKey)
    }
  } finally {
    await browser.close()
  }
  console.log('\nDone. PNGs in', __dirname)
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
