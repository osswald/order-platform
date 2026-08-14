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

  it('applies greyscale class from gallery flag', () => {
    expect(src).toMatch(/screensaverGreyscale/)
    expect(src).toMatch(/screensaver-image--greyscale/)
    expect(src).toMatch(/filter:\s*grayscale\(1\)/)
  })
})

describe('RegisterDisplayView success pickup badges', () => {
  const src = readFileSync(viewPath, 'utf8')

  it('shows the station name under each pickup code', () => {
    expect(src).toMatch(/pickupBadgesForDisplay/)
    expect(src).toMatch(/pickup-badge-code/)
    expect(src).toMatch(/pickup-badge-station/)
    expect(src).toMatch(/badge\.stationName/)
    expect(src).toMatch(/\.pickup-badge[\s\S]*flex-direction:\s*column/)
  })
})
