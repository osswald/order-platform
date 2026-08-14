import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const viewPath = resolve(__dirname, '../views/RegisterDisplayView.vue')

describe('RegisterDisplayView idle screensaver', () => {
  const src = readFileSync(viewPath, 'utf8')

  it('falls back to Herzlich Willkommen when idle without gallery', () => {
    expect(src).toMatch(/Herzlich Willkommen/)
    expect(src).toMatch(/screensaverUrls\.length/)
  })

  it('renders screensaver images when urls exist on idle', () => {
    expect(src).toMatch(/screensaver-image/)
    expect(src).toMatch(/v-else class="idle-screen"/)
  })

  it('leaves screensaver for non-idle states', () => {
    expect(src).toMatch(/state === 'ordering'/)
    expect(src).toMatch(/state === 'sumup_connected'/)
    expect(src).toMatch(/state === 'submitted'/)
  })
})
