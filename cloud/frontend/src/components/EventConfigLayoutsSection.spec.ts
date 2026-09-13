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

  it('removes a configured cell when delete is confirmed', async () => {
    const confirmMock = vi.fn(() => true)
    vi.stubGlobal('confirm', confirmMock)
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
              cells: [
                {
                  row: 0,
                  col: 0,
                  label: 'Beer',
                  color: '#ffcc00',
                  article_ids: [10],
                  voucher_definition_uuid: null,
                  voucher_definition_uuids: [],
                },
              ],
            },
          ],
        }
      }
      if (path === '/events/42/station-article-tree') {
        return { nodes: [] }
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

    expect(layouts[0].cells).toHaveLength(1)

    await wrapper.find('.grid-cell').trigger('click')
    await flushPromises()

    const deleteBtn = wrapper.find('[data-testid="delete-layout-cell-btn"]')
    expect(deleteBtn.exists()).toBe(true)
    await deleteBtn.trigger('click')
    await flushPromises()

    expect(confirmMock).toHaveBeenCalled()
    expect(layouts[0].cells).toEqual([])
    vi.unstubAllGlobals()
  })

  it('removes a configured cell when apply clears all articles and vouchers', async () => {
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
              cells: [
                {
                  row: 0,
                  col: 0,
                  label: 'Beer',
                  color: '#ffcc00',
                  article_ids: [10],
                  voucher_definition_uuid: null,
                  voucher_definition_uuids: [],
                },
              ],
            },
          ],
        }
      }
      if (path === '/events/42/station-article-tree') {
        return { nodes: [] }
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

    await wrapper.find('.grid-cell').trigger('click')
    await flushPromises()

    const vm = wrapper.vm as unknown as {
      cellEdit: { label: string; article_ids: number[]; voucher_definition_uuids: string[] }
      cellTreeSelection: string[]
    }
    vm.cellEdit.label = ''
    vm.cellEdit.article_ids = []
    vm.cellEdit.voucher_definition_uuids = []
    vm.cellTreeSelection = []

    const applyBtn = wrapper.findAll('button').find((b) => b.text().includes('Übernehmen'))
    expect(applyBtn).toBeDefined()
    await applyBtn!.trigger('click')
    await flushPromises()

    expect(layouts[0].cells).toEqual([])
  })

  it('shows empty state when event articles prop has no station articles', async () => {
    apiJsonMock.mockResolvedValue({
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
        eventArticles: [],
        modelValue: layouts,
        'onUpdate:modelValue': (value: EventLayoutLocal[]) => {
          layouts.splice(0, layouts.length, ...value)
        },
      },
      global: {
        stubs: {
          ...vuetifyStubs(),
          'v-dialog': { template: '<div><slot /></div>' },
          'v-treeview': { template: '<div class="v-treeview-stub" />' },
        },
      },
    })

    await flushPromises()
    await wrapper.find('.grid-cell').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-testid="cell-article-tree-empty"]').exists()).toBe(true)
    expect(apiJsonMock.mock.calls.some((c) => String(c[0]).includes('station-article-tree'))).toBe(
      false,
    )
  })

  it('shows error when station-article-tree fetch fails without eventArticles', async () => {
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
      if (path === '/events/42/station-article-tree') {
        throw new Error('network')
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
        modelValue: layouts,
        'onUpdate:modelValue': (value: EventLayoutLocal[]) => {
          layouts.splice(0, layouts.length, ...value)
        },
      },
      global: {
        stubs: {
          ...vuetifyStubs(),
          'v-dialog': { template: '<div><slot /></div>' },
          'v-treeview': { template: '<div class="v-treeview-stub" />' },
        },
      },
    })

    await flushPromises()
    await wrapper.find('.grid-cell').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-testid="cell-article-tree-error"]').exists()).toBe(true)
  })

  it('renders station articles from eventArticles prop in the cell dialog', async () => {
    apiJsonMock.mockResolvedValue({
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
        eventArticles: [
          {
            id: 10,
            name: 'Bratwurst',
            label: 'BW',
            price: 8,
            article_category_id: 1,
            article_category_name: 'Food',
            is_addition: false,
            is_active: true,
            organisation_id: 1,
            organisation_name: 'Org',
            organisation_currency: 'CHF',
          },
        ],
        modelValue: layouts,
        'onUpdate:modelValue': (value: EventLayoutLocal[]) => {
          layouts.splice(0, layouts.length, ...value)
        },
      },
      global: {
        stubs: {
          ...vuetifyStubs(),
          'v-dialog': { template: '<div><slot /></div>' },
          'v-treeview': {
            props: ['items'],
            template: '<div class="v-treeview-stub">{{ items?.[0]?.title }} {{ items?.[0]?.children?.[0]?.title }}</div>',
          },
        },
      },
    })

    await flushPromises()
    await wrapper.find('.grid-cell').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-testid="cell-article-tree-empty"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="cell-article-tree-error"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('Food')
    expect(wrapper.text()).toContain('BW — Bratwurst')
  })

  it('shows locked-Zusatz checklist for one article with no vouchers', async () => {
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
              cells: [
                {
                  row: 0,
                  col: 0,
                  label: 'Combo',
                  color: '#ffcc00',
                  article_ids: [10],
                  voucher_definition_uuid: null,
                  voucher_definition_uuids: [],
                  locked_addition_ids: [20],
                },
              ],
            },
          ],
        }
      }
      if (path === '/articles/10/additions') {
        return {
          items: [
            { addition_article_id: 20, name: 'Käse' },
            { addition_article_id: 21, name: 'Speck' },
          ],
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
        eventArticles: [
          {
            id: 10,
            name: 'Bratwurst',
            label: 'BW',
            price: 8,
            article_category_id: 1,
            article_category_name: 'Food',
            is_addition: false,
            is_active: true,
            organisation_id: 1,
            organisation_name: 'Org',
            organisation_currency: 'CHF',
          },
        ],
        modelValue: layouts,
        'onUpdate:modelValue': (value: EventLayoutLocal[]) => {
          layouts.splice(0, layouts.length, ...value)
        },
      },
      global: {
        stubs: {
          ...vuetifyStubs(),
          'v-dialog': { template: '<div><slot /></div>' },
          'v-treeview': { template: '<div class="v-treeview-stub" />' },
          'v-checkbox': {
            props: ['modelValue', 'label'],
            template: '<label class="v-checkbox-stub">{{ label }}</label>',
          },
          'v-progress-linear': { template: '<div class="v-progress-linear-stub" />' },
        },
      },
    })

    await flushPromises()
    await wrapper.find('.grid-cell').trigger('click')
    await flushPromises()

    expect(apiJsonMock).toHaveBeenCalledWith('/articles/10/additions')
    expect(wrapper.find('[data-testid="locked-additions"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Käse')
    expect(wrapper.text()).toContain('Speck')

    const vm = wrapper.vm as unknown as { cellEdit: { locked_addition_ids: number[] } }
    expect(vm.cellEdit.locked_addition_ids).toEqual([20])
  })

  it('clears locked additions when a second article is selected', async () => {
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
              cells: [
                {
                  row: 0,
                  col: 0,
                  label: 'Combo',
                  color: '#ffcc00',
                  article_ids: [10],
                  voucher_definition_uuids: [],
                  locked_addition_ids: [20],
                },
              ],
            },
          ],
        }
      }
      if (path === '/articles/10/additions') {
        return { items: [{ addition_article_id: 20, name: 'Käse' }] }
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
        eventArticles: [
          {
            id: 10,
            name: 'Bratwurst',
            label: 'BW',
            price: 8,
            article_category_id: 1,
            article_category_name: 'Food',
            is_addition: false,
            is_active: true,
            organisation_id: 1,
            organisation_name: 'Org',
            organisation_currency: 'CHF',
          },
          {
            id: 11,
            name: 'Pommes',
            label: 'PF',
            price: 5,
            article_category_id: 1,
            article_category_name: 'Food',
            is_addition: false,
            is_active: true,
            organisation_id: 1,
            organisation_name: 'Org',
            organisation_currency: 'CHF',
          },
        ],
        modelValue: layouts,
        'onUpdate:modelValue': (value: EventLayoutLocal[]) => {
          layouts.splice(0, layouts.length, ...value)
        },
      },
      global: {
        stubs: {
          ...vuetifyStubs(),
          'v-dialog': { template: '<div><slot /></div>' },
          'v-treeview': { template: '<div class="v-treeview-stub" />' },
        },
      },
    })

    await flushPromises()
    await wrapper.find('.grid-cell').trigger('click')
    await flushPromises()

    const vm = wrapper.vm as unknown as {
      cellEdit: { locked_addition_ids: number[]; voucher_definition_uuids: string[] }
      cellTreeSelection: string[]
    }
    expect(vm.cellEdit.locked_addition_ids).toEqual([20])
    expect(wrapper.find('[data-testid="locked-additions"]').exists()).toBe(true)

    vm.cellTreeSelection = ['art-10', 'art-11']
    await flushPromises()

    expect(vm.cellEdit.locked_addition_ids).toEqual([])
    expect(wrapper.find('[data-testid="locked-additions"]').exists()).toBe(false)
  })

  it('clears locked additions when a voucher is selected', async () => {
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
              cells: [
                {
                  row: 0,
                  col: 0,
                  label: 'Combo',
                  color: '#ffcc00',
                  article_ids: [10],
                  voucher_definition_uuids: [],
                  locked_addition_ids: [20],
                },
              ],
            },
          ],
        }
      }
      if (path === '/articles/10/additions') {
        return { items: [{ addition_article_id: 20, name: 'Käse' }] }
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
        vouchersEnabled: true,
        voucherDefinitions: [
          {
            uuid: 'v-1',
            name: '10er',
            kind: 'fixed_amount',
            value_amount: 10,
            allowed_article_ids: [],
            include_additions: false,
          },
        ],
        eventArticles: [
          {
            id: 10,
            name: 'Bratwurst',
            label: 'BW',
            price: 8,
            article_category_id: 1,
            article_category_name: 'Food',
            is_addition: false,
            is_active: true,
            organisation_id: 1,
            organisation_name: 'Org',
            organisation_currency: 'CHF',
          },
        ],
        modelValue: layouts,
        'onUpdate:modelValue': (value: EventLayoutLocal[]) => {
          layouts.splice(0, layouts.length, ...value)
        },
      },
      global: {
        stubs: {
          ...vuetifyStubs(),
          'v-dialog': { template: '<div><slot /></div>' },
          'v-treeview': { template: '<div class="v-treeview-stub" />' },
        },
      },
    })

    await flushPromises()
    await wrapper.find('.grid-cell').trigger('click')
    await flushPromises()

    const vm = wrapper.vm as unknown as {
      cellEdit: { locked_addition_ids: number[]; voucher_definition_uuids: string[] }
    }
    expect(vm.cellEdit.locked_addition_ids).toEqual([20])

    vm.cellEdit.voucher_definition_uuids = ['v-1']
    await flushPromises()

    expect(vm.cellEdit.locked_addition_ids).toEqual([])
    expect(wrapper.find('[data-testid="locked-additions"]').exists()).toBe(false)
  })

  it('keeps locked_addition_ids when article selection briefly empties then restores', async () => {
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
              cells: [
                {
                  row: 0,
                  col: 0,
                  label: 'Combo',
                  color: '#ffcc00',
                  article_ids: [10],
                  voucher_definition_uuids: [],
                  locked_addition_ids: [20],
                },
              ],
            },
          ],
        }
      }
      if (path === '/articles/10/additions') {
        return { items: [{ addition_article_id: 20, name: 'Käse' }] }
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
        eventArticles: [
          {
            id: 10,
            name: 'Bratwurst',
            label: 'BW',
            price: 8,
            article_category_id: 1,
            article_category_name: 'Food',
            is_addition: false,
            is_active: true,
            organisation_id: 1,
            organisation_name: 'Org',
            organisation_currency: 'CHF',
          },
        ],
        modelValue: layouts,
        'onUpdate:modelValue': (value: EventLayoutLocal[]) => {
          layouts.splice(0, layouts.length, ...value)
        },
      },
      global: {
        stubs: {
          ...vuetifyStubs(),
          'v-dialog': { template: '<div><slot /></div>' },
          'v-treeview': { template: '<div class="v-treeview-stub" />' },
        },
      },
    })

    await flushPromises()
    await wrapper.find('.grid-cell').trigger('click')
    await flushPromises()

    const vm = wrapper.vm as unknown as {
      cellEdit: { locked_addition_ids: number[] }
      cellTreeSelection: string[]
    }
    expect(vm.cellEdit.locked_addition_ids).toEqual([20])

    vm.cellTreeSelection = []
    await flushPromises()
    vm.cellTreeSelection = ['art-10']
    await flushPromises()

    expect(vm.cellEdit.locked_addition_ids).toEqual([20])
    expect(wrapper.find('[data-testid="locked-additions"]').exists()).toBe(true)
  })

  it('clears locked additions when the single base article changes', async () => {
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
              cells: [
                {
                  row: 0,
                  col: 0,
                  label: 'Combo',
                  color: '#ffcc00',
                  article_ids: [10],
                  voucher_definition_uuids: [],
                  locked_addition_ids: [20],
                },
              ],
            },
          ],
        }
      }
      if (path === '/articles/10/additions') {
        return { items: [{ addition_article_id: 20, name: 'Käse' }] }
      }
      if (path === '/articles/11/additions') {
        return { items: [{ addition_article_id: 30, name: 'Ketchup' }] }
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
        eventArticles: [
          {
            id: 10,
            name: 'Bratwurst',
            label: 'BW',
            price: 8,
            article_category_id: 1,
            article_category_name: 'Food',
            is_addition: false,
            is_active: true,
            organisation_id: 1,
            organisation_name: 'Org',
            organisation_currency: 'CHF',
          },
          {
            id: 11,
            name: 'Pommes',
            label: 'PF',
            price: 5,
            article_category_id: 1,
            article_category_name: 'Food',
            is_addition: false,
            is_active: true,
            organisation_id: 1,
            organisation_name: 'Org',
            organisation_currency: 'CHF',
          },
        ],
        modelValue: layouts,
        'onUpdate:modelValue': (value: EventLayoutLocal[]) => {
          layouts.splice(0, layouts.length, ...value)
        },
      },
      global: {
        stubs: {
          ...vuetifyStubs(),
          'v-dialog': { template: '<div><slot /></div>' },
          'v-treeview': { template: '<div class="v-treeview-stub" />' },
        },
      },
    })

    await flushPromises()
    await wrapper.find('.grid-cell').trigger('click')
    await flushPromises()

    const vm = wrapper.vm as unknown as {
      cellEdit: { locked_addition_ids: number[] }
      cellTreeSelection: string[]
    }
    expect(vm.cellEdit.locked_addition_ids).toEqual([20])

    vm.cellTreeSelection = ['art-11']
    await flushPromises()

    expect(vm.cellEdit.locked_addition_ids).toEqual([])
  })

  it('drops orphan locked_addition_ids after Zusatz options load', async () => {
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
              cells: [
                {
                  row: 0,
                  col: 0,
                  label: 'Combo',
                  color: '#ffcc00',
                  article_ids: [10],
                  voucher_definition_uuids: [],
                  locked_addition_ids: [20, 99],
                },
              ],
            },
          ],
        }
      }
      if (path === '/articles/10/additions') {
        return { items: [{ addition_article_id: 20, name: 'Käse' }] }
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
        eventArticles: [
          {
            id: 10,
            name: 'Bratwurst',
            label: 'BW',
            price: 8,
            article_category_id: 1,
            article_category_name: 'Food',
            is_addition: false,
            is_active: true,
            organisation_id: 1,
            organisation_name: 'Org',
            organisation_currency: 'CHF',
          },
        ],
        modelValue: layouts,
        'onUpdate:modelValue': (value: EventLayoutLocal[]) => {
          layouts.splice(0, layouts.length, ...value)
        },
      },
      global: {
        stubs: {
          ...vuetifyStubs(),
          'v-dialog': { template: '<div><slot /></div>' },
          'v-treeview': { template: '<div class="v-treeview-stub" />' },
        },
      },
    })

    await flushPromises()
    await wrapper.find('.grid-cell').trigger('click')
    await flushPromises()

    const vm = wrapper.vm as unknown as { cellEdit: { locked_addition_ids: number[] } }
    expect(vm.cellEdit.locked_addition_ids).toEqual([20])
  })

  it('persists locked_addition_ids when applying the cell dialog', async () => {
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
              cells: [
                {
                  row: 0,
                  col: 0,
                  label: 'Combo',
                  color: '#ffcc00',
                  article_ids: [10],
                  voucher_definition_uuids: [],
                  locked_addition_ids: [],
                },
              ],
            },
          ],
        }
      }
      if (path === '/articles/10/additions') {
        return {
          items: [
            { addition_article_id: 20, name: 'Käse' },
            { addition_article_id: 21, name: 'Speck' },
          ],
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
        eventArticles: [
          {
            id: 10,
            name: 'Bratwurst',
            label: 'BW',
            price: 8,
            article_category_id: 1,
            article_category_name: 'Food',
            is_addition: false,
            is_active: true,
            organisation_id: 1,
            organisation_name: 'Org',
            organisation_currency: 'CHF',
          },
        ],
        modelValue: layouts,
        'onUpdate:modelValue': (value: EventLayoutLocal[]) => {
          layouts.splice(0, layouts.length, ...value)
        },
      },
      global: {
        stubs: {
          ...vuetifyStubs(),
          'v-dialog': { template: '<div><slot /></div>' },
          'v-treeview': { template: '<div class="v-treeview-stub" />' },
        },
      },
    })

    await flushPromises()
    await wrapper.find('.grid-cell').trigger('click')
    await flushPromises()

    const vm = wrapper.vm as unknown as {
      cellEdit: { locked_addition_ids: number[] }
      cellTreeSelection: string[]
    }
    vm.cellTreeSelection = ['art-10']
    vm.cellEdit.locked_addition_ids = [20, 21]
    await flushPromises()

    const applyBtn = wrapper.findAll('button').find((b) => b.text().includes('Übernehmen'))
    expect(applyBtn).toBeDefined()
    await applyBtn!.trigger('click')
    await flushPromises()

    expect(layouts[0].cells[0].locked_addition_ids).toEqual([20, 21])
  })
})
