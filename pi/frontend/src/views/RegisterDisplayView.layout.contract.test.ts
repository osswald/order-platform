import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const viewPath = resolve(__dirname, '../views/RegisterDisplayView.vue')

describe('RegisterDisplayView overflow layout', () => {
  it('reserves scrollbar gutter and uses stable price column', () => {
    const src = readFileSync(viewPath, 'utf8')
    expect(src).toMatch(/scrollbar-gutter:\s*stable/)
    expect(src).toMatch(/grid-template-columns/)
  })
})
