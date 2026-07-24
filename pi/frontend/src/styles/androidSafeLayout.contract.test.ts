/// <reference types="node" />
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const srcRoot = join(dirname(fileURLToPath(import.meta.url)), '..')

function readSrc(...parts: string[]): string {
  return readFileSync(join(srcRoot, ...parts), 'utf8')
}

/** Extract a CSS rule body for `selector` (first `{...}` block after the selector text). */
function ruleBody(css: string, selector: string): string {
  const idx = css.indexOf(selector)
  expect(idx, `missing selector: ${selector}`).toBeGreaterThanOrEqual(0)
  const brace = css.indexOf('{', idx)
  expect(brace).toBeGreaterThan(idx)
  let depth = 0
  for (let i = brace; i < css.length; i++) {
    if (css[i] === '{') depth++
    else if (css[i] === '}') {
      depth--
      if (depth === 0) return css.slice(brace + 1, i)
    }
  }
  throw new Error(`unclosed rule for ${selector}`)
}

describe('android fullscreen safe layout (CSS contract)', () => {
  const appCss = readSrc('styles', 'app.css')

  it('gives hosted-demo shell a definite height under html.android-app', () => {
    const body = ruleBody(appCss, 'html.android-app .hosted-demo-shell')
    expect(body).toMatch(/height:\s*100%/)
    expect(body).toMatch(/min-height:\s*0/)
  })

  it('gives hosted-demo app a definite height under html.android-app', () => {
    const body = ruleBody(appCss, 'html.android-app .hosted-demo-app')
    expect(body).toMatch(/height:\s*100%/)
    expect(body).toMatch(/min-height:\s*0/)
  })

  it('keeps fullscreen POS roots on the android height + inset chain', () => {
    const body = ruleBody(appCss, 'html.android-app .order-screen,\nhtml.android-app .split-pay-screen')
    expect(body).toMatch(/height:\s*100%/)
    expect(body).toMatch(/padding-top:\s*var\(--safe-top\)/)
    expect(body).toMatch(/padding-bottom:\s*var\(--safe-bottom\)/)
  })

  it('does not pad app-main--fullscreen (avoids double safe-top with screen roots)', () => {
    const body = ruleBody(appCss, 'html.android-app .app-main--fullscreen')
    expect(body).not.toMatch(/padding-top:\s*var\(--safe-top\)/)
    expect(body).toMatch(/height:\s*100%/)
  })

  it('preserves non-fullscreen app-main top inset', () => {
    const body = ruleBody(appCss, 'html.android-app .app-main:not(.app-main--fullscreen)')
    expect(body).toMatch(/padding-top:\s*calc\(0\.75rem \+ var\(--safe-top\)\)/)
  })

  it('keeps wide hosted-demo as a side-by-side grid', () => {
    const body = ruleBody(appCss, '.hosted-demo-shell--wide')
    expect(body).toMatch(/display:\s*grid/)
    expect(body).toMatch(/grid-template-columns:/)
  })
})

describe('android fullscreen safe layout (sheet sources)', () => {
  it('TwintQrSheet pads safe-top and safe-bottom', () => {
    const vue = readSrc('components', 'TwintQrSheet.vue')
    expect(vue).toMatch(
      /padding:\s*calc\(1rem \+ var\(--safe-top\)\)\s+1rem\s+calc\(1rem \+ var\(--safe-bottom\)\)/,
    )
  })
})
