import { beforeEach, describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import AdditionsPickerSheet from './AdditionsPickerSheet.vue'
import type { EdgeBundleArticleAddition } from '@/types/api'
import * as store from '@/store'
import { bundleWithStock } from '@tests/fixtures/bundle'
import { resetStore } from '@tests/helpers/resetStore'

function addition(overrides: Partial<EdgeBundleArticleAddition> & { article_id: number }): EdgeBundleArticleAddition {
  return {
    name: `Addon ${overrides.article_id}`,
    price: 1.0,
    sellable: true,
    monitor_stock: false,
    ...overrides,
  }
}

function openSheet(
  additions: EdgeBundleArticleAddition[],
  open = true,
) {
  return mount(AdditionsPickerSheet, {
    props: {
      open,
      articleName: 'Burger',
      additions,
      currency: 'CHF',
    },
    global: {
      stubs: {
        Teleport: true,
      },
    },
  })
}

function checkboxFor(wrapper: ReturnType<typeof mount>, articleId: number) {
  const inputs = wrapper.findAll('input[type="checkbox"]')
  const idx = additionsIndex(wrapper, articleId)
  return inputs[idx]!
}

function additionsIndex(wrapper: ReturnType<typeof mount>, articleId: number) {
  const ids = wrapper.findAll('li.sheet-option-row').map((row, i) => {
    const name = row.find('.sheet-option-row__name').text()
    return { i, name }
  })
  const match = ids.find((x) => x.name === `Addon ${articleId}` || x.name === 'mit Salat')
  expect(match).toBeTruthy()
  return match!.i
}

describe('AdditionsPickerSheet', () => {
  beforeEach(() => {
    resetStore()
    store.bundle.value = bundleWithStock()
    store.selectedEventId.value = 1
  })

  it('preselects additions flagged preselected when opened', async () => {
    const wrapper = openSheet([
      addition({ article_id: 1, preselected: true }),
      addition({ article_id: 2, preselected: false }),
    ])
    await nextTick()
    expect(checkboxFor(wrapper, 1).element).toHaveProperty('checked', true)
    expect(checkboxFor(wrapper, 2).element).toHaveProperty('checked', false)
    wrapper.unmount()
  })

  it('does not preselect sold-out additions', async () => {
    const wrapper = openSheet([
      addition({
        article_id: 1,
        preselected: true,
        monitor_stock: true,
        in_stock: 0,
        sellable: false,
      }),
    ])
    await nextTick()
    expect(checkboxFor(wrapper, 1).element).toHaveProperty('checked', false)
    wrapper.unmount()
  })

  it('disables ingredient-based sold-out additions', async () => {
    resetStore()
    const b = bundleWithStock()
    const ev = b.events![0]!
    ev.ingredients = {
      '1': { id: 1, name: 'Kartoffelsalat', monitor_stock: true, in_stock: 0 },
    }
    ev.articles!['3'] = {
      id: 3,
      name: 'mit Salat',
      price: 1.0,
      is_addition: true,
      ingredients: [{ ingredient_id: 1, amount: 0.5 }],
      sellable: false,
    }
    store.bundle.value = b
    store.selectedEventId.value = 1

    const wrapper = openSheet([addition({ article_id: 3, name: 'mit Salat', sellable: false })])
    await nextTick()
    expect(checkboxFor(wrapper, 3).attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain('ausverkauft')
    wrapper.unmount()
  })

  it('allows deselecting a preselected addition before confirm', async () => {
    const wrapper = openSheet([addition({ article_id: 1, preselected: true })])
    await nextTick()
    const input = checkboxFor(wrapper, 1)
    expect(input.element).toHaveProperty('checked', true)
    await input.setValue(false)
    await wrapper.find('button.primary').trigger('click')
    expect(wrapper.emitted('confirm')?.[0]).toEqual([[]])
    wrapper.unmount()
  })

  it('confirms with preselected additions by default', async () => {
    const wrapper = openSheet([
      addition({ article_id: 1, preselected: true }),
      addition({ article_id: 2, preselected: true }),
    ])
    await nextTick()
    await wrapper.find('button.primary').trigger('click')
    expect(wrapper.emitted('confirm')?.[0]).toEqual([
      [
        { article_id: 1, qty: 1 },
        { article_id: 2, qty: 1 },
      ],
    ])
    wrapper.unmount()
  })
})
