import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import RentalZubehoerCatalogSection from './RentalZubehoerCatalogSection.vue'
import de from '../locales/de.json'
import { vuetifyStubs } from '../../tests/helpers/vuetifyStub.js'

vi.mock('../api', () => ({
  apiJson: vi.fn(),
}))

import { apiJson } from '../api'

const i18n = createI18n({ legacy: false, locale: 'de', messages: { de } })

describe('RentalZubehoerCatalogSection', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(apiJson).mockResolvedValue([])
  })

  it('loads catalog when hire company id is set', async () => {
    mount(RentalZubehoerCatalogSection, {
      props: { hireCompanyId: 1 },
      global: {
        plugins: [i18n],
        stubs: {
          ...vuetifyStubs(),
          'v-dialog': { template: '<div v-if="modelValue"><slot /></div>', props: ['modelValue'] },
          'v-card': { template: '<div><slot /></div>' },
          'v-card-title': { template: '<div><slot /></div>' },
          'v-card-text': { template: '<div><slot /></div>' },
          'v-card-actions': { template: '<div><slot /></div>' },
          'v-spacer': { template: '<div />' },
        },
      },
    })
    await flushPromises()
    expect(apiJson).toHaveBeenCalledWith('/rental-zubehoer-catalog/')
  })
})
