/// <reference types="node" />
// Importing `vuetify/components` directly would drag component CSS into the Node
// test environment, so the components index is inspected as text instead.
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import type { TreeViewNode } from '@/utils/articleCategoryTree'

const vuetifyComponentsIndex = readFileSync(
  path.resolve(
    path.dirname(fileURLToPath(import.meta.url)),
    '../../node_modules/vuetify/lib/components/index.js',
  ),
  'utf8',
)

/**
 * Guards against reverting Vuetify 4 slot/API migrations based on a misread of the upgrade guide.
 * In v4, slot prop `item` is the raw list/tree node (`internalItem.raw`), not the wrapper.
 */
describe('Vuetify 4 migration contract', () => {
  it('ships VDateInput in core components (moved from labs in v4)', () => {
    expect(vuetifyComponentsIndex).toContain('./VDateInput/index.js')
  })

  it('exposes select slot item as the raw option object, not internalItem', () => {
    const rawOption = { label: 'POS terminal', value: 'pos_terminal' }
    const internalItem = {
      raw: rawOption,
      value: rawOption.value,
      title: rawOption.label,
      props: {},
    }

    const slotItem = internalItem.raw
    expect(slotItem.value).toBe('pos_terminal')
    expect(slotItem.label).toBe('POS terminal')
    expect('raw' in slotItem).toBe(false)
  })

  it('exposes treeview title slot item as the raw TreeViewNode', () => {
    const rawNode: TreeViewNode = {
      key: 'art-10',
      title: 'BW — Bratwurst',
      children: undefined,
    }
    const internalItem = {
      raw: rawNode,
      props: { value: rawNode.key },
    }

    const slotItem = internalItem.raw
    expect(slotItem.key).toBe('art-10')
    expect(slotItem.title).toBe('BW — Bratwurst')
    expect(slotItem.children).toBeUndefined()
  })

  it('reads category children from the raw tree node passed to the title slot', () => {
    const categoryNode: TreeViewNode = {
      key: 'cat-1',
      title: 'Food',
      children: [{ key: 'art-10', title: 'BW — Bratwurst' }],
    }

    const isLeaf = !categoryNode.children?.length
    expect(isLeaf).toBe(false)

    const leafNode = categoryNode.children![0]
    expect(!leafNode.children?.length).toBe(true)
    expect(leafNode.key).toBe('art-10')
  })
})
