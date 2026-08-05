/// <reference types="node" />
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const routerSrc = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), 'index.ts'),
  'utf8',
)

/** Grab the meta object for the first route whose `name:` matches. */
function metaForRouteName(name: string): string {
  const nameRe = new RegExp(`name:\\s*'${name}'`)
  const nameIdx = routerSrc.search(nameRe)
  expect(nameIdx, `route name ${name}`).toBeGreaterThanOrEqual(0)
  const metaIdx = routerSrc.indexOf('meta:', nameIdx)
  expect(metaIdx, `meta for ${name}`).toBeGreaterThan(nameIdx)
  const brace = routerSrc.indexOf('{', metaIdx)
  expect(brace).toBeGreaterThan(metaIdx)
  let depth = 0
  for (let i = brace; i < routerSrc.length; i++) {
    if (routerSrc[i] === '{') depth++
    else if (routerSrc[i] === '}') {
      depth--
      if (depth === 0) return routerSrc.slice(brace, i + 1)
    }
  }
  throw new Error(`unclosed meta for ${name}`)
}

describe('router immersive meta', () => {
  it('marks kitchen, pickup, and register-display as immersive', () => {
    for (const name of ['kitchen', 'pickup', 'register-display'] as const) {
      expect(metaForRouteName(name)).toMatch(/immersive:\s*true/)
    }
  })

  it('keeps order and pay-table non-immersive (fullscreen only)', () => {
    expect(metaForRouteName('order')).toMatch(/fullscreen:\s*true/)
    expect(metaForRouteName('order')).not.toMatch(/immersive:\s*true/)
    expect(metaForRouteName('pay-table')).toMatch(/fullscreen:\s*true/)
    expect(metaForRouteName('pay-table')).not.toMatch(/immersive:\s*true/)
    expect(metaForRouteName('register-order')).toMatch(/fullscreen:\s*true/)
    expect(metaForRouteName('register-order')).not.toMatch(/immersive:\s*true/)
  })
})
