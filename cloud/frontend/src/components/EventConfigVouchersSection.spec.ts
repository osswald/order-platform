import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import EventConfigVouchersSection from './EventConfigVouchersSection.vue'
import type { EventVoucherDefinitionLocal } from '@/types/ui'
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
  article({ id: 10, name: 'Beer', label: 'B1', article_category_name: 'Drinks' }),
  article({ id: 20, name: 'Wine', label: 'W1', article_category_name: 'Drinks' }),
]

const globalMount = {
  global: {
    stubs: {
      ...vuetifyStubs(),
      FormLabel: { template: '<label><slot /></label>' },
      'v-select': { template: '<select />', props: ['modelValue', 'items'] },
      'v-number-input': {
        template: '<input type="number" :value="modelValue" />',
        props: ['modelValue'],
      },
      'v-checkbox': { template: '<input type="checkbox" />', props: ['modelValue'] },
      StationArticleTransferPicker: {
        template:
          '<div data-testid="article-transfer-picker" :data-articles-count="articles.length"><button data-testid="add-article" type="button" @click="$emit(\'update:modelValue\', [42])">add</button></div>',
        props: ['modelValue', 'articles', 'loading', 'disabled'],
      },
      'v-btn': {
        template: '<button type="button" @click="$emit(\'click\')"><slot /></button>',
        props: ['icon', 'variant', 'color', 'disabled'],
      },
    },
  },
}

function articleEntitlementVoucher(): EventVoucherDefinitionLocal {
  return {
    uuid: 'vd-1',
    name: 'Free beer',
    kind: 'article_entitlement',
    value_amount: 0,
    allowed_article_ids: [],
    include_additions: true,
  }
}

describe('EventConfigVouchersSection', () => {
  it('shows catalog loading hint', () => {
    const wrapper = mount(EventConfigVouchersSection, {
      props: {
        modelValue: [],
        catalogLoading: true,
        catalogError: '',
        articles: [],
        currencyLabel: 'CHF',
        voucherKindOptions: [],
      },
      ...globalMount,
    })
    expect(wrapper.text()).toContain('Artikel und Kellner werden geladen')
  })

  it('renders article transfer picker only for article_entitlement vouchers', () => {
    const wrapper = mount(EventConfigVouchersSection, {
      props: {
        modelValue: [
          {
            uuid: 'vd-fixed',
            name: 'CHF 10',
            kind: 'fixed_amount',
            value_amount: 10,
            allowed_article_ids: [],
            include_additions: true,
          },
          articleEntitlementVoucher(),
        ],
        catalogLoading: false,
        catalogError: '',
        articles: sampleArticles,
        currencyLabel: 'CHF',
        voucherKindOptions: [],
      },
      ...globalMount,
    })
    expect(wrapper.findAll('[data-testid="article-transfer-picker"]')).toHaveLength(1)
  })

  it('passes event-scoped articles to the transfer picker', () => {
    const wrapper = mount(EventConfigVouchersSection, {
      props: {
        modelValue: [articleEntitlementVoucher()],
        catalogLoading: false,
        catalogError: '',
        articles: [sampleArticles[0]],
        currencyLabel: 'CHF',
        voucherKindOptions: [],
      },
      ...globalMount,
    })
    const picker = wrapper.find('[data-testid="article-transfer-picker"]')
    expect(picker.attributes('data-articles-count')).toBe('1')
  })

  it('binds article transfer picker to allowed_article_ids', async () => {
    const vouchers: EventVoucherDefinitionLocal[] = [articleEntitlementVoucher()]
    const wrapper = mount(EventConfigVouchersSection, {
      props: {
        modelValue: vouchers,
        'onUpdate:modelValue': (v: EventVoucherDefinitionLocal[]) => {
          vouchers.splice(0, vouchers.length, ...v)
        },
        catalogLoading: false,
        catalogError: '',
        articles: sampleArticles,
        currencyLabel: 'CHF',
        voucherKindOptions: [],
      },
      ...globalMount,
    })
    await wrapper.find('[data-testid="add-article"]').trigger('click')
    expect(vouchers[0].allowed_article_ids).toEqual([42])
  })
})
