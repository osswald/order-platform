import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import EventConfigLayoutsSection from './EventConfigLayoutsSection.vue'
import type { EventLayoutLocal } from '@/types/ui'
import { vuetifyStubs } from '../../tests/helpers/vuetifyStub.js'

const apiJsonMock = vi.fn()

vi.mock('../api', () => ({
  apiJson: (...args: unknown[]) => apiJsonMock(...args),
}))

describe('EventConfigLayoutsSection', () => {
  it('loads layout cells when mounted so the add button becomes available', async () => {
    apiJsonMock.mockResolvedValue({
      app_layouts: [
        {
          uuid: 'layout-1',
          name: 'Main',
          is_default: true,
          grid_width: 2,
          grid_height: 2,
          cells: [],
        },
      ],
    })

    const layouts: EventLayoutLocal[] = [
      {
        uuid: 'layout-1',
        name: 'Main',
        is_default: true,
        grid_width: 2,
        grid_height: 2,
        cells: [],
      },
    ]

    const wrapper = mount(EventConfigLayoutsSection, {
      props: {
        eventId: 42,
        modelValue: layouts,
        'onUpdate:modelValue': (value: EventLayoutLocal[]) => {
          layouts.splice(0, layouts.length, ...value)
        },
      },
      global: {
        stubs: {
          ...vuetifyStubs(),
          'v-dialog': { template: '<div><slot /></div>' },
        },
      },
    })

    await flushPromises()

    expect(apiJsonMock).toHaveBeenCalledWith('/events/42/configuration')
    expect(wrapper.text()).toContain('Layout hinzufügen')
  })
})
