import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import { createMemoryHistory, createRouter } from 'vue-router'
import RentalsCalendar from './RentalsCalendar.vue'
import de from '../locales/de.json'
import { vuetifyStubs } from '../../tests/helpers/vuetifyStub.js'

vi.mock('../api', () => ({
  apiJson: vi.fn(),
  apiFetch: vi.fn(),
}))

import { apiFetch, apiJson } from '../api'

const org = { id: 9, name: 'FC St.Gallen' }
const rental = {
  id: 42,
  hire_company_id: 1,
  organisation_id: 9,
  organisation_name: 'FC St.Gallen',
  start_date: '2026-06-12',
  end_date: '2026-06-15',
  label: 'Openair 2026',
  display_name: 'Openair 2026',
  filled: false,
  lendings: [] as Array<Record<string, unknown>>,
  zubehoer_lines: [] as Array<Record<string, unknown>>,
}

const catalogItem = { id: 5, name: 'Thermopapier', default_quantity: 2, sort_order: 0, is_active: true }

const i18n = createI18n({
  legacy: false,
  locale: 'de',
  messages: { de },
})

let deletedRentalIds = new Set<number>()

function mockListPayload(rows = [rental]) {
  vi.mocked(apiJson).mockImplementation(async (path: string, init?: RequestInit) => {
    if (path === '/organisations/') return [org]
    if (path === '/rental-zubehoer-catalog/') return [catalogItem]
    if (path.startsWith('/rentals/?from=')) {
      return rows.filter((row) => !deletedRentalIds.has(row.id))
    }
    if (path === '/rentals/42') return rows[0] ?? rental
    if (path === '/rentals/' && init?.method === 'POST') return { ...rental, id: 99 }
    if (path === '/rentals/42' && init?.method === 'PATCH') {
      const body = JSON.parse(String(init.body))
      return { ...rental, ...body, organisation_id: 9, organisation_name: 'FC St.Gallen', display_name: body.label || 'FC St.Gallen' }
    }
    if (path === '/rentals/42' && init?.method === 'DELETE') {
      deletedRentalIds.add(42)
      return null
    }
    if (path === '/rentals/42/zubehoer-lines' && init?.method === 'POST') {
      const body = JSON.parse(String(init.body))
      return {
        id: 11,
        rental_id: 42,
        catalog_item_id: body.catalog_item_id ?? null,
        label: body.label ?? catalogItem.name,
        quantity: body.quantity ?? catalogItem.default_quantity,
        sort_order: 0,
      }
    }
    if (path.startsWith('/rentals/42/zubehoer-lines/') && init?.method === 'PATCH') {
      const body = JSON.parse(String(init.body))
      return {
        id: 11,
        rental_id: 42,
        catalog_item_id: null,
        label: body.label,
        quantity: body.quantity ?? null,
        sort_order: 0,
      }
    }
    if (path.startsWith('/rentals/42/zubehoer-lines/') && init?.method === 'DELETE') return null
    if (path.startsWith('/rentals/42/lendings/') && init?.method === 'DELETE') {
      return { ...rental, lendings: [] }
    }
    if (path === '/rentals/42/appliances' && init?.method === 'POST') {
      const body = JSON.parse(String(init.body))
      return {
        ...rental,
        filled: true,
        lendings: [
          {
            id: 8,
            appliance_id: body.appliance_id,
            appliance_name: 'Pi-01',
            appliance_type: 'server',
            start_date: rental.start_date,
            end_date: rental.end_date,
            returned_at: null,
            segment: 'future',
          },
        ],
      }
    }
    if (path.startsWith('/appliances/?')) {
      return [{ id: 3, name: 'Pi-02', type: 'server', lendable: true }]
    }
    if (path.startsWith('/rentals/fleet')) return { year: 2026, month: 6, groups: [] }
    throw new Error(`unexpected ${init?.method || 'GET'} ${path}`)
  })
}

async function mountCalendar(path = '/rentals') {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/rentals', name: 'rentals', component: RentalsCalendar }],
  })
  await router.push(path)
  await router.isReady()
  const wrapper = mount(RentalsCalendar, {
    global: {
      plugins: [router, i18n],
      stubs: {
        ...vuetifyStubs(),
        HelpLink: { template: '<div />' },
        ApplianceTypeChip: {
          props: ['type'],
          template: '<span v-bind="$attrs" :data-type="type">{{ type }}</span>',
        },
        'v-tooltip': {
          template:
            '<div class="v-tooltip-stub"><slot name="activator" :props="{}" /><div class="v-tooltip-content"><slot /></div></div>',
        },
        'v-dialog': { template: '<div v-if="modelValue"><slot /></div>', props: ['modelValue'] },
        'v-card': { template: '<div><slot /></div>' },
        'v-card-title': { template: '<div class="card-title"><slot /></div>' },
        'v-card-text': { template: '<div class="card-text"><slot /></div>' },
        'v-card-actions': { template: '<div class="card-actions"><slot /></div>' },
        'v-spacer': { template: '<div />' },
        'v-list-item': { template: '<div class="v-list-item"><slot /></div>' },
        'v-btn-toggle': {
          props: ['modelValue'],
          emits: ['update:modelValue'],
          template: '<div class="btn-toggle" @click="onToggleClick"><slot /></div>',
          methods: {
            onToggleClick(event: MouseEvent) {
              const target = event.target as HTMLElement | null
              const btn = target?.closest?.('[data-value]') as HTMLElement | null
              const value = btn?.getAttribute('data-value')
              if (value) this.$emit('update:modelValue', value)
            },
          },
        },
        'v-btn': {
          props: ['modelValue', 'value', 'loading', 'color', 'block', 'size', 'variant', 'icon'],
          emits: ['click'],
          inheritAttrs: false,
          template:
            '<button type="button" v-bind="$attrs" :data-color="color" :data-variant="variant" :data-icon="icon" :data-value="value" @click="$emit(\'click\', $event)"><slot /></button>',
        },
        'v-text-field': {
          props: ['modelValue', 'label', 'type', 'rules'],
          emits: ['update:modelValue'],
          inheritAttrs: false,
          template:
            '<label><span v-if="label">{{ label }}</span><input v-bind="$attrs" :type="type || \'text\'" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" /></label>',
        },
        'v-select': {
          props: ['modelValue', 'label', 'disabled', 'items', 'itemTitle', 'itemValue', 'loading', 'clearable'],
          emits: ['update:modelValue'],
          inheritAttrs: false,
          template:
            '<div class="v-select-stub" v-bind="$attrs">' +
            '<select :disabled="disabled" :aria-label="label" @change="$emit(\'update:modelValue\', Number($event.target.value))">' +
            '<option v-for="item in items || []" :key="item.value" :value="item.value">{{ item.title }}</option>' +
            '</select>' +
            '<div v-for="item in items || []" :key="`slot-${item.value}`" class="v-select-item-slot">' +
            '<slot name="item" :item="{ raw: item, title: item.title, value: item.value }" :props="{}" />' +
            '</div>' +
            '</div>',
        },
      },
    },
  })
  await flushPromises()
  return wrapper
}

describe('RentalsCalendar edit', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-06-01T12:00:00Z'))
    deletedRentalIds = new Set()
    mockListPayload()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders a multi-day rental as week-spanning bars, not one chip per day', async () => {
    const wrapper = await mountCalendar()
    // Fri–Mon spans two week rows → two bars, not four daily chips.
    expect(wrapper.findAll('[data-testid="month-rental-bar"]')).toHaveLength(2)
  })

  it('shows rental info and appliances in month bar tooltips', async () => {
    mockListPayload([
      {
        ...rental,
        lendings: [
          {
            id: 8,
            appliance_id: 3,
            appliance_name: 'Pi-01',
            appliance_type: 'server',
            start_date: rental.start_date,
            end_date: rental.end_date,
            returned_at: null,
            segment: 'future',
          },
        ],
      },
    ])
    const wrapper = await mountCalendar()
    const tip = wrapper.find('[data-testid="rental-bar-tooltip"]')
    expect(tip.exists()).toBe(true)
    expect(tip.text()).toContain('Openair 2026')
    expect(tip.text()).toContain('FC St.Gallen')
    expect(tip.text()).toContain('Geräte')
    expect(tip.text()).toContain('Pi-01')
  })

  it('stacks overlapping year rentals on separate lanes', async () => {
    mockListPayload([
      rental,
      {
        ...rental,
        id: 43,
        label: 'Overlap',
        display_name: 'Overlap',
        start_date: '2026-06-12',
        end_date: '2026-06-15',
      },
    ])
    const wrapper = await mountCalendar()
    ;(wrapper.vm as { setViewForTest: (v: string) => void }).setViewForTest('year')
    await flushPromises()
    const bars = wrapper.findAll('[data-testid="year-rental-bar"]')
    expect(bars).toHaveLength(2)
    const tops = bars.map((bar) => (bar.attributes('style') || '').match(/top:\s*([^;]+)/)?.[1])
    expect(tops[0]).toBeTruthy()
    expect(tops[1]).toBeTruthy()
    expect(tops[0]).not.toBe(tops[1])
  })

  it('opens edit when clicking a month rental bar, not create', async () => {
    const wrapper = await mountCalendar()
    const chip = wrapper.find('[data-testid="month-rental-bar"]')
    expect(chip.exists()).toBe(true)
    await chip.trigger('click')
    await flushPromises()
    expect(apiJson).toHaveBeenCalledWith('/rentals/42')
    expect(wrapper.find('.card-title').text()).toContain('Ausleihe bearbeiten')
    expect(wrapper.find('[data-testid="org-readonly"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="org-select"]').exists()).toBe(false)
    const posts = vi.mocked(apiJson).mock.calls.filter((call) => call[1]?.method === 'POST')
    expect(posts).toHaveLength(0)
  })

  it('opens create when clicking an empty day cell', async () => {
    mockListPayload([])
    const wrapper = await mountCalendar()
    const day = wrapper.findAll('.day-cell').find((el) => el.text().includes('10'))
    expect(day).toBeTruthy()
    await day!.trigger('click')
    await flushPromises()
    expect(wrapper.find('.card-title').text()).toContain('Ausleihe anlegen')
    expect(wrapper.find('[data-testid="org-select"]').exists()).toBe(true)
  })

  it('opens edit when clicking a year rental bar', async () => {
    const wrapper = await mountCalendar()
    ;(wrapper.vm as { setViewForTest: (v: string) => void }).setViewForTest('year')
    await flushPromises()
    const bar = wrapper.find('[data-testid="year-rental-bar"]')
    expect(bar.exists()).toBe(true)
    await bar.trigger('click')
    await flushPromises()
    expect(apiJson).toHaveBeenCalledWith('/rentals/42')
    expect(wrapper.find('.card-title').text()).toContain('Ausleihe bearbeiten')
  })

  it('PATCHes label and dates on save', async () => {
    const wrapper = await mountCalendar()
    await wrapper.find('[data-testid="month-rental-bar"]').trigger('click')
    await flushPromises()
    const labelInput = wrapper.findAll('input').find((el) => el.attributes('type') !== 'date')!
    await labelInput.setValue('Updated')
    await wrapper.find('[data-testid="rental-save"]').trigger('click')
    await flushPromises()
    const patch = vi.mocked(apiJson).mock.calls.find((call) => call[0] === '/rentals/42' && call[1]?.method === 'PATCH')
    expect(patch).toBeTruthy()
    expect(JSON.parse(String(patch![1]?.body))).toMatchObject({
      label: 'Updated',
      start_date: '2026-06-12',
      end_date: '2026-06-15',
    })
  })

  it('shows delete for empty rental and DELETEs on confirm', async () => {
    vi.stubGlobal('confirm', vi.fn(() => true))
    const wrapper = await mountCalendar()
    await wrapper.find('[data-testid="month-rental-bar"]').trigger('click')
    await flushPromises()
    const del = wrapper.find('[data-testid="rental-delete"]')
    expect(del.exists()).toBe(true)
    await del.trigger('click')
    await flushPromises()
    expect(apiJson).toHaveBeenCalledWith('/rentals/42', expect.objectContaining({ method: 'DELETE' }))
    const listCalls = vi.mocked(apiJson).mock.calls.filter((call) => String(call[0]).startsWith('/rentals/?from='))
    expect(listCalls.length).toBeGreaterThanOrEqual(2)
    expect(wrapper.find('.month-grid').isVisible()).toBe(true)
    expect(wrapper.find('[data-testid="rentals-message"]').text()).toContain('gelöscht')
    expect(wrapper.findAll('[data-testid="month-rental-bar"]')).toHaveLength(0)
    vi.unstubAllGlobals()
  })

  it('adds zubehoer free-text line in edit dialog', async () => {
    const wrapper = await mountCalendar()
    await wrapper.find('[data-testid="month-rental-bar"]').trigger('click')
    await flushPromises()
    const labelInput = wrapper.find('[data-testid="zubehoer-free-text"]')
    await labelInput.setValue('Kabelbinder')
    await wrapper.find('[data-testid="zubehoer-add-free-text"]').trigger('click')
    await flushPromises()
    expect(apiJson).toHaveBeenCalledWith(
      '/rentals/42/zubehoer-lines',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ label: 'Kabelbinder' }),
      }),
    )
  })

  it('adds zubehoer from catalog with chosen quantity', async () => {
    const wrapper = await mountCalendar()
    await wrapper.find('[data-testid="month-rental-bar"]').trigger('click')
    await flushPromises()
    const pick = wrapper.find('[data-testid="zubehoer-catalog-pick"] select')
    await pick.setValue('5')
    await pick.trigger('change')
    await flushPromises()
    expect((wrapper.find('[data-testid="zubehoer-catalog-qty"]').element as HTMLInputElement).value).toBe(
      '2',
    )
    await wrapper.find('[data-testid="zubehoer-catalog-qty"]').setValue('4')
    await wrapper.find('[data-testid="zubehoer-add-catalog"]').trigger('click')
    await flushPromises()
    expect(apiJson).toHaveBeenCalledWith(
      '/rentals/42/zubehoer-lines',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ catalog_item_id: 5, quantity: 4 }),
      }),
    )
  })

  it('edits an existing zubehoer line via PATCH', async () => {
    mockListPayload([
      {
        ...rental,
        zubehoer_lines: [
          {
            id: 11,
            rental_id: 42,
            catalog_item_id: null,
            label: 'Kabelbinder',
            quantity: 2,
            sort_order: 0,
          },
        ],
      },
    ])
    const wrapper = await mountCalendar()
    await wrapper.find('[data-testid="month-rental-bar"]').trigger('click')
    await flushPromises()
    await wrapper.find('[data-testid="zubehoer-line-edit"]').trigger('click')
    await wrapper.find('[data-testid="zubehoer-edit-label"]').setValue('Kabelbinder XL')
    await wrapper.find('[data-testid="zubehoer-edit-qty"]').setValue('5')
    await wrapper.find('[data-testid="zubehoer-line-save"]').trigger('click')
    await flushPromises()
    expect(apiJson).toHaveBeenCalledWith(
      '/rentals/42/zubehoer-lines/11',
      expect.objectContaining({
        method: 'PATCH',
        body: JSON.stringify({ label: 'Kabelbinder XL', quantity: 5 }),
      }),
    )
  })

  it('shows printer IP in the assigned appliances list', async () => {
    mockListPayload([
      {
        ...rental,
        filled: true,
        lendings: [
          {
            id: 7,
            appliance_id: 9,
            appliance_name: 'Zephyrus',
            appliance_type: 'printer',
            appliance_ip_address: '192.168.1.50',
            start_date: '2026-06-12',
            end_date: '2026-06-15',
            returned_at: null,
            segment: 'future',
          },
        ],
      },
    ])
    const wrapper = await mountCalendar()
    await wrapper.find('[data-testid="month-rental-bar"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('.lending-label').text()).toContain('Zephyrus (192.168.1.50)')
  })

  it('labels the devices view tab as Geräte', async () => {
    const wrapper = await mountCalendar()
    expect(wrapper.find('[data-testid="view-fleet"]').text()).toContain('Geräte')
  })

  it('downloads packing list pdf from edit dialog', async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      ok: true,
      blob: async () => new Blob(['%PDF'], { type: 'application/pdf' }),
    } as Response)
    const wrapper = await mountCalendar()
    await wrapper.find('[data-testid="month-rental-bar"]').trigger('click')
    await flushPromises()
    await wrapper.find('[data-testid="rental-packing-pdf"]').trigger('click')
    await flushPromises()
    expect(apiFetch).toHaveBeenCalledWith(
      '/rentals/42/packing-list.pdf',
      expect.objectContaining({ headers: expect.objectContaining({ 'Accept-Language': 'de' }) }),
    )
  })

  it('hides delete when a current lending exists', async () => {
    mockListPayload([
      {
        ...rental,
        filled: true,
        lendings: [
          {
            id: 7,
            appliance_id: 1,
            appliance_name: 'Pi-01',
            appliance_type: 'server',
            start_date: '2026-06-12',
            end_date: '2026-06-15',
            returned_at: null,
            segment: 'current',
          },
        ],
      },
    ])
    const wrapper = await mountCalendar()
    await wrapper.find('[data-testid="month-rental-bar"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-testid="rental-delete"]').exists()).toBe(false)
  })

  it('shows appliance type chips in the assigned list and add dropdown', async () => {
    mockListPayload([
      {
        ...rental,
        filled: true,
        lendings: [
          {
            id: 7,
            appliance_id: 1,
            appliance_name: 'Pi-01',
            appliance_type: 'server',
            start_date: '2026-06-12',
            end_date: '2026-06-15',
            returned_at: null,
            segment: 'future',
          },
        ],
      },
    ])
    const wrapper = await mountCalendar()
    await wrapper.find('[data-testid="month-rental-bar"]').trigger('click')
    await flushPromises()
    const assigned = wrapper.find('[data-testid="lending-appliance-type"]')
    expect(assigned.exists()).toBe(true)
    expect(assigned.attributes('data-type')).toBe('server')
    const addChip = wrapper.find('[data-testid="add-appliance-type"]')
    expect(addChip.exists()).toBe(true)
    expect(addChip.attributes('data-type')).toBe('server')
  })

  it('unassigns a planned lending via DELETE lendings endpoint', async () => {
    mockListPayload([
      {
        ...rental,
        filled: true,
        lendings: [
          {
            id: 8,
            appliance_id: 1,
            appliance_name: 'Pi-01',
            appliance_type: 'server',
            start_date: '2026-06-12',
            end_date: '2026-06-15',
            returned_at: null,
            segment: 'future',
          },
        ],
      },
    ])
    const wrapper = await mountCalendar()
    await wrapper.find('[data-testid="month-rental-bar"]').trigger('click')
    await flushPromises()
    await wrapper.find('[data-testid="lending-unassign"]').trigger('click')
    await flushPromises()
    expect(apiJson).toHaveBeenCalledWith(
      '/rentals/42/lendings/8',
      expect.objectContaining({ method: 'DELETE' }),
    )
  })

  it('adds an appliance from the edit dialog', async () => {
    const wrapper = await mountCalendar()
    await wrapper.find('[data-testid="month-rental-bar"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-testid="rental-add-appliance-pick"]').exists()).toBe(true)
    const vm = wrapper.vm as {
      setPickApplianceIdForTest: (id: number | null) => void
      addApplianceToRentalForTest: () => Promise<void>
    }
    vm.setPickApplianceIdForTest(3)
    await vm.addApplianceToRentalForTest()
    await flushPromises()
    expect(apiJson).toHaveBeenCalledWith(
      '/rentals/42/appliances',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ appliance_id: 3 }),
      }),
    )
  })

  it('shows add-device overlap error from API', async () => {
    vi.mocked(apiJson).mockImplementation(async (path: string, init?: RequestInit) => {
      if (path === '/organisations/') return [org]
      if (path === '/rental-zubehoer-catalog/') return [catalogItem]
      if (path.startsWith('/rentals/?from=')) return [rental]
      if (path === '/rentals/42') return rental
      if (path.startsWith('/appliances/?')) return [{ id: 3, name: 'Pi-02', type: 'server', lendable: true }]
      if (path === '/rentals/42/appliances' && init?.method === 'POST') {
        throw Object.assign(new Error('lending_overlap'), { status: 400 })
      }
      if (path.startsWith('/rentals/fleet')) return { year: 2026, month: 6, groups: [] }
      throw new Error(`unexpected ${init?.method || 'GET'} ${path}`)
    })
    const wrapper = await mountCalendar()
    await wrapper.find('[data-testid="month-rental-bar"]').trigger('click')
    await flushPromises()
    const vm = wrapper.vm as {
      setPickApplianceIdForTest: (id: number | null) => void
      addApplianceToRentalForTest: () => Promise<void>
    }
    vm.setPickApplianceIdForTest(3)
    await vm.addApplianceToRentalForTest()
    await flushPromises()
    expect(wrapper.text()).toContain('lending_overlap')
  })
})
