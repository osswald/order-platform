import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const viewPath = resolve(__dirname, '../views/RegisterDisplayView.vue')

describe('RegisterDisplayView overflow layout', () => {
  const src = readFileSync(viewPath, 'utf8')

  it('does not reuse the POS order-body two-column grid class', () => {
    expect(src).not.toMatch(/class="order-body"/)
    expect(src).not.toMatch(/['"]order-body--scrolled['"]/)
    expect(src).toMatch(/display-order-body/)
  })

  it('keeps the line list in a single full-width column', () => {
    expect(src).toMatch(/\.display-order-body[\s\S]*display:\s*flex/)
    expect(src).toMatch(/\.display-order-body[\s\S]*flex-direction:\s*column/)
    expect(src).toMatch(/\.display-order-body[\s\S]*width:\s*100%/)
    expect(src).toMatch(/grid-template-columns/)
    expect(src).toMatch(/scrollbar-gutter:\s*stable/)
  })
})
