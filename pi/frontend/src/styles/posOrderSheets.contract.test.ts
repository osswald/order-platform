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

describe('POS order picker sheets (CSS contract)', () => {
  const appCss = readSrc('styles', 'app.css')

  it('picker option buttons inherit sheet font size and family', () => {
    const body = ruleBody(appCss, '.sheet--picker .sheet-option-row__control--btn')
    expect(body).toMatch(/font:\s*inherit/)
  })

  it('picker option buttons keep Zusätze row padding and a .btn-floor min-height', () => {
    const control = ruleBody(appCss, '.sheet-option-row__control')
    expect(control).toMatch(/padding:\s*0\.85rem\s+0\.25rem/)
    const btn = ruleBody(appCss, '.sheet--picker .sheet-option-row__control--btn')
    expect(btn).toMatch(/min-height:\s*44px/)
  })
})

describe('LayoutCellPickerSheet footer (source contract)', () => {
  it('Abbrechen uses shared .btn metrics without an extra 48px min-height', () => {
    const vue = readSrc('components', 'LayoutCellPickerSheet.vue')
    expect(vue).toMatch(/class="btn"[^>]*>Abbrechen/)
    expect(vue).not.toMatch(/\.sheet__footer\s+\.btn\s*\{[^}]*min-height:\s*48px/)
  })
})

describe('TwintQrSheet viewport fill (source contract)', () => {
  it('fills the viewport and pins Fertig then Abbrechen at the end of the column', () => {
    const vue = readSrc('components', 'TwintQrSheet.vue')
    const sheet = ruleBody(vue, '.twint-qr-sheet')
    expect(sheet).toMatch(/inset:\s*0/)
    expect(sheet).toMatch(/max-height:\s*none/)
    expect(sheet).toMatch(/height:\s*100%/)
    expect(sheet).toMatch(/overflow:\s*hidden/)
    expect(sheet).toMatch(/flex-direction:\s*column/)
    expect(sheet).not.toMatch(/max-height:\s*70vh/)

    const actionsIdx = vue.indexOf('class="sheet-actions"')
    expect(actionsIdx).toBeGreaterThan(0)
    const fertigIdx = vue.indexOf('>Fertig<', actionsIdx)
    const abbrechenIdx = vue.indexOf('>Abbrechen<', actionsIdx)
    expect(fertigIdx).toBeGreaterThan(actionsIdx)
    expect(abbrechenIdx).toBeGreaterThan(fertigIdx)

    const qrWrap = ruleBody(vue, '.qr-wrap')
    expect(qrWrap).toMatch(/flex:\s*1/)
    expect(qrWrap).toMatch(/padding:\s*1rem\s*;/)
    expect(qrWrap).not.toMatch(/padding:\s*1rem\s+0/)

    const qrImage = ruleBody(vue, '.qr-image')
    expect(qrImage).toMatch(/width:\s*100%/)
    expect(qrImage).toMatch(/height:\s*100%/)
    expect(qrImage).toMatch(/object-fit:\s*contain/)
    expect(qrImage).not.toMatch(/360px/)
    expect(qrImage).not.toMatch(/60vh/)
  })
})
