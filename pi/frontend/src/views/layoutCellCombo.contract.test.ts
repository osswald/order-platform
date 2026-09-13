/// <reference types="node" />
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const srcRoot = join(dirname(fileURLToPath(import.meta.url)), '..')

function readSrc(...parts: string[]): string {
  return readFileSync(join(srcRoot, ...parts), 'utf8')
}

describe('layout cell combo one-tap (source contract)', () => {
  it('EventLayoutGrid emits locked addition ids for combo cells', () => {
    const vue = readSrc('components', 'EventLayoutGrid.vue')
    expect(vue).toMatch(/locked_addition_ids\?:/)
    expect(vue).toMatch(/isLayoutCellEnabled/)
    expect(vue).toMatch(/isAdditionSellable/)
    expect(vue).toMatch(/emit\('pick',\s*\[one\.article_id\],\s*locked\)/)
  })

  for (const view of ['OrderView.vue', 'RegisterOrderView.vue'] as const) {
    it(`${view} skips Zusätze sheet when lockedAdditionIds options are present`, () => {
      const vue = readSrc('views', view)
      expect(vue).toMatch(/shouldSkipAdditionsSheet/)
      expect(vue).toMatch(/cartAdditionsFromLockedIds/)
      expect(vue).toMatch(/BeginAddOptions/)
      expect(vue).toMatch(/lockedIds && lockedIds\.length > 0/)
      expect(vue).toMatch(/beginAdd\([^)]*\{\s*lockedAdditionIds:\s*lockedIds\s*\}/)
    })
  }
})
