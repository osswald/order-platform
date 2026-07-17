import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import StationArticleTransferPicker from './StationArticleTransferPicker.vue'
import type { ArticleRead } from '@/types/api'
import { vuetifyStubs } from '../../tests/helpers/vuetifyStub.js'

function article(overrides: Partial<ArticleRead> & Pick<ArticleRead, 'id'>): ArticleRead {
  return {
    name: 'Item',
    label: 'ITEM',
    price: 1,
    article_category_id: 1,
    is_addition: false,
    is_active: true,
    article_category_name: 'Cat',
    organisation_id: 1,
    organisation_name: 'Org',
    organisation_currency: 'CHF',
    ...overrides,
  }
}

const sampleArticles: ArticleRead[] = [
  article({
    id: 10,
    name: 'Bratwurst',
    label: 'BW',
    article_category_id: 1,
    article_category_name: 'Food',
  }),
  article({
    id: 11,
    name: 'Bier',
    label: 'BI',
    article_category_id: 2,
    article_category_name: 'Drinks',
  }),
]

const globalMount = {
  global: {
    stubs: {
      ...vuetifyStubs(),
      ArticleCategoryTreeList: {
        template:
          '<div data-testid="tree-list"><button data-testid="pick-10" type="button" @click="$emit(\'pick-article\', 10)">pick food</button><button data-testid="pick-11" type="button" @click="$emit(\'pick-article\', 11)">pick drink</button></div>',
        props: ['items', 'loading', 'filterPlaceholder', 'pickAriaLabel'],
      },
      'v-list': { template: '<div class="v-list"><slot /></div>' },
      'v-list-group': {
        template: '<div class="v-list-group"><slot name="activator" :props="{}" /><slot /></div>',
      },
      'v-list-item': {
        template: '<div v-bind="$attrs" @click="$emit(\'click\')">{{ title }}</div>',
        props: ['title'],
        inheritAttrs: false,
      },
      'v-progress-linear': true,
    },
  },
}

describe('StationArticleTransferPicker', () => {
  it('shows panel headings and empty selected hint', () => {
    const wrapper = mount(StationArticleTransferPicker, {
      props: {
        articles: sampleArticles,
        modelValue: [],
      },
      ...globalMount,
    })
    expect(wrapper.text()).toContain('Verfügbare Artikel')
    expect(wrapper.text()).toContain('Ausgewählte Artikel')
    expect(wrapper.text()).toContain('Noch keine Artikel ausgewählt.')
  })

  it('adds article when tree emits pick-article', async () => {
    const wrapper = mount(StationArticleTransferPicker, {
      props: {
        articles: sampleArticles,
        modelValue: [] as number[],
        'onUpdate:modelValue': (value: number[]) => wrapper.setProps({ modelValue: value }),
      },
      ...globalMount,
    })
    await wrapper.find('[data-testid="pick-10"]').trigger('click')
    expect(wrapper.props('modelValue')).toEqual([10])
    expect(wrapper.find('[data-testid="selected-article-10"]').exists()).toBe(true)
  })

  it('removes article when selected item is clicked', async () => {
    const wrapper = mount(StationArticleTransferPicker, {
      props: {
        articles: sampleArticles,
        modelValue: [10, 11],
        'onUpdate:modelValue': (value: number[]) => wrapper.setProps({ modelValue: value }),
      },
      ...globalMount,
    })
    await wrapper.find('[data-testid="selected-article-11"]').trigger('click')
    expect(wrapper.props('modelValue')).toEqual([10])
  })

  it('does not add duplicate article ids', async () => {
    const wrapper = mount(StationArticleTransferPicker, {
      props: {
        articles: sampleArticles,
        modelValue: [10],
        'onUpdate:modelValue': (value: number[]) => wrapper.setProps({ modelValue: value }),
      },
      ...globalMount,
    })
    await wrapper.find('[data-testid="pick-10"]').trigger('click')
    expect(wrapper.props('modelValue')).toEqual([10])
  })

  it('filters selected articles by search query', async () => {
    const wrapper = mount(StationArticleTransferPicker, {
      props: {
        articles: sampleArticles,
        modelValue: [10, 11],
      },
      global: {
        stubs: {
          ...globalMount.global.stubs,
          ArticleCategoryTreeList: true,
          'v-text-field': {
            template:
              '<input :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
            props: ['modelValue'],
          },
        },
      },
    })
    const inputs = wrapper.findAll('input')
    const selectedFilter = inputs.at(inputs.length - 1)
    expect(selectedFilter).toBeDefined()
    await selectedFilter!.setValue('bier')
    expect(wrapper.text()).toContain('BI — Bier')
    expect(wrapper.text()).not.toContain('BW — Bratwurst')
  })
})
