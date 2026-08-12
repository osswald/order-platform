import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import { createMemoryHistory, createRouter } from 'vue-router'
import RentalsCalendar from './RentalsCalendar.vue'
import de from '../locales/de.json'
import { vuetifyStubs } from '../../tests/helpers/vuetifyStub.js'

vi.mock('../api', () => ({
  apiJson: vi.fn(),
}))

import { apiJson } from '../api'

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
}

const i18n = createI18n({
  legacy: false,
  locale: 'de',
  messages: { de },
})

function mockListPayload(rows = [rental]) {
  vi.mocked(apiJson).mockImplementation(async (path: string, init?: RequestInit) => {
    if (path === '/organisations/') return [org]
    if (path.startsWith('/rentals/?from=')) return rows
    if (path === '/rentals/42') return rows[0] ?? rental
    if (path === '/rentals/' && init?.method === 'POST') return { ...rental, id: 99 }
    if (path === '/rentals/42' && init?.method === 'PATCH') {
      const body = JSON.parse(String(init.body))
      return { ...rental, ...body, organisation_id: 9, organisation_name: 'FC St.Gallen', display_name: body.label || 'FC St.Gallen' }
    }
    if (path === '/rentals/42' && init?.method === 'DELETE') return null
    if (path.startsWith('/rentals/42/lendings/') && init?.method === 'DELETE') {
      return { ...rental, lendings: [] }
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
        ApplianceTypeChip: { template: '<span />' },
        'v-dialog': { template: '<div v-if="modelValue"><slot /></div>', props: ['modelValue'] },
        'v-card': { template: '<div><slot /></div>' },
        'v-card-title': { template: '<div class="card-title"><slot /></div>' },
        'v-card-text': { template: '<div class="card-text"><slot /></div>' },
        'v-card-actions': { template: '<div class="card-actions"><slot /></div>' },
        'v-spacer': { template: '<div />' },
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
          template:
            '<label>{{ label }}<input :type="type || \'text\'" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" /></label>',
        },
        'v-select': {
          props: ['modelValue', 'label', 'disabled', 'items', 'itemTitle', 'itemValue'],
          template:
            '<select data-testid="org-select" :disabled="disabled" :aria-label="label" @change="$emit(\'update:modelValue\', Number($event.target.value))"></select>',
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
    mockListPayload()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('opens edit when clicking a month rental bar, not create', async () => {
    const wrapper = await mountCalendar()
    const chip = wrapper.find('.rental-chip')
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
    const bar = wrapper.find('.year-bar')
    expect(bar.exists()).toBe(true)
    await bar.trigger('click')
    await flushPromises()
    expect(apiJson).toHaveBeenCalledWith('/rentals/42')
    expect(wrapper.find('.card-title').text()).toContain('Ausleihe bearbeiten')
  })

  it('PATCHes label and dates on save', async () => {
    const wrapper = await mountCalendar()
    await wrapper.find('.rental-chip').trigger('click')
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
    await wrapper.find('.rental-chip').trigger('click')
    await flushPromises()
    const del = wrapper.find('[data-testid="rental-delete"]')
    expect(del.exists()).toBe(true)
    await del.trigger('click')
    await flushPromises()
    expect(apiJson).toHaveBeenCalledWith('/rentals/42', expect.objectContaining({ method: 'DELETE' }))
    vi.unstubAllGlobals()
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
    await wrapper.find('.rental-chip').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-testid="rental-delete"]').exists()).toBe(false)
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
    await wrapper.find('.rental-chip').trigger('click')
    await flushPromises()
    await wrapper.find('[data-testid="lending-unassign"]').trigger('click')
    await flushPromises()
    expect(apiJson).toHaveBeenCalledWith(
      '/rentals/42/lendings/8',
      expect.objectContaining({ method: 'DELETE' }),
    )
  })
})
