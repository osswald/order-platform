import { mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import { describe, expect, it, vi } from 'vitest'
import OrderjutsuImportWizard from './OrderjutsuImportWizard.vue'

vi.mock('@/api', () => ({
  apiJson: vi.fn(async (path: string) => {
    if (path.includes('article-categories')) return [{ id: 1, name: 'Food' }]
    return null
  }),
}))

vi.mock('@/composables/useOrgCatalog', () => ({
  loadOrgCatalog: vi.fn(async () => ({ articles: [], waiters: [], fromCache: false })),
}))

const i18n = createI18n({
  legacy: false,
  locale: 'de',
  messages: {
    de: {
      common: { cancel: 'Abbrechen', back: 'Zurück', next: 'Weiter', emDash: '—' },
      events: {
        table: { name: 'Name', start: 'Start', end: 'Ende' },
        config: { waiter: 'Kellner', station: 'Station', layout: 'Layout' },
        importOrderjutsu: 'Import',
        import: {
          orderjutsu: {
            title: 'Import',
            subtitle: 'Sub',
            uploadHint: 'Hint',
            chooseFile: 'Choose',
            steps: {
              upload: 'Upload',
              event: 'Event',
              review: 'Review',
            },
          },
        },
      },
    },
  },
})

describe('OrderjutsuImportWizard', () => {
  it('renders upload step initially', () => {
    const wrapper = mount(OrderjutsuImportWizard, {
      props: { activeOrganisationId: 1 },
      global: {
        plugins: [i18n],
        stubs: {
          VqDataTable: { template: '<div class="vq-data-table" />' },
          'v-stepper': { template: '<div><slot /></div>' },
          'v-stepper-header': { template: '<div><slot /></div>' },
          'v-stepper-item': { template: '<div><slot /></div>' },
          'v-stepper-window': { template: '<div><slot /></div>' },
          'v-stepper-window-item': { template: '<div><slot /></div>' },
          'v-card': { template: '<div><slot /></div>' },
          'v-btn': { template: '<button><slot /></button>' },
          'v-spacer': true,
          'v-divider': true,
          'v-text-field': true,
          'v-select': true,
          'v-checkbox': true,
          'v-alert': true,
        },
      },
    })
    expect(wrapper.text()).toContain('Hint')
  })
})
