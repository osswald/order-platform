import { describe, expect, it, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import EventConfigLayoutsSection from './EventConfigLayoutsSection.vue'
import type { EventLayoutLocal } from '@/types/ui'
import { vuetifyStubs } from '../../tests/helpers/vuetifyStub.js'

const apiJsonMock = vi.fn()

vi.mock('../api', () => ({
  apiJson: (...args: unknown[]) => apiJsonMock(...args),
}))

describe('EventConfigLayoutsSection', () => {
  beforeEach(() => {
    apiJsonMock.mockReset()
  })

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

  it('shows organisation palette swatches with labels when palette is defined', async () => {
    apiJsonMock.mockImplementation(async (path: string) => {
      if (path === '/events/42/configuration') {
        return {
          app_layouts: [
            {
              uuid: 'layout-1',
              name: 'Main',
              is_default: true,
              grid_width: 1,
              grid_height: 1,
              cells: [],
            },
          ],
        }
      }
      if (path === '/organisations/7/color-palette') {
        return {
          colors: [{ label: 'Primary', color: '#FF0000' }],
        }
      }
      return {}
    })

    const layouts: EventLayoutLocal[] = [
      {
        uuid: 'layout-1',
        name: 'Main',
        is_default: true,
        grid_width: 1,
        grid_height: 1,
        cells: [],
      },
    ]

    const wrapper = mount(EventConfigLayoutsSection, {
      props: {
        eventId: 42,
        organisationId: 7,
        modelValue: layouts,
        cellDialogOpen: true,
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

    expect(apiJsonMock).toHaveBeenCalledWith('/organisations/7/color-palette')
    expect(wrapper.text()).toContain('Organisationsfarben')
    expect(wrapper.text()).toContain('Primary')
    expect(wrapper.find('.org-palette-swatch').exists()).toBe(true)
  })

  it('hides organisation palette swatches when palette is empty', async () => {
    apiJsonMock.mockImplementation(async (path: string) => {
      if (path === '/events/42/configuration') {
        return {
          app_layouts: [
            {
              uuid: 'layout-1',
              name: 'Main',
              is_default: true,
              grid_width: 1,
              grid_height: 1,
              cells: [],
            },
          ],
        }
      }
      if (path === '/organisations/7/color-palette') {
        return { colors: [] }
      }
      return {}
    })

    const layouts: EventLayoutLocal[] = [
      {
        uuid: 'layout-1',
        name: 'Main',
        is_default: true,
        grid_width: 1,
        grid_height: 1,
        cells: [],
      },
    ]

    const wrapper = mount(EventConfigLayoutsSection, {
      props: {
        eventId: 42,
        organisationId: 7,
        modelValue: layouts,
        cellDialogOpen: true,
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

    expect(wrapper.text()).not.toContain('Organisationsfarben')
    expect(wrapper.find('.org-palette-swatch').exists()).toBe(false)
  })
})
