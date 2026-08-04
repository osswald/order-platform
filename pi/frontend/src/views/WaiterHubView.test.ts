import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { computed, ref } from 'vue'
import type { EdgeBundleEvent, EdgeBundleResponse } from '@/types/api'
import * as store from '@/store'

const ctx = vi.hoisted(() => ({
  push: vi.fn(),
  setWaiter: vi.fn(),
  maybeEndShiftOnSwitch: vi.fn(async () => true),
  ensureReachable: vi.fn(async () => true),
  event: null as ReturnType<typeof ref<EdgeBundleEvent | null>> | null,
  waiter: null as ReturnType<
    typeof ref<{
      uuid: string
      name: string
      sumupReaderId?: string
      sumupReaderLabel?: string
    }>
  > | null,
  selectedEventId: null as ReturnType<typeof ref<number>> | null,
  status: null as ReturnType<typeof ref<'unknown' | 'reachable' | 'unreachable'>> | null,
  probing: null as ReturnType<typeof ref<boolean>> | null,
}))

vi.mock('@/api', () => ({
  isAndroidApp: vi.fn(() => false),
}))

vi.mock('@/composables/useEventContext', () => ({
  useEventContext: () => ({
    event: ctx.event,
    waiter: ctx.waiter,
    setWaiter: ctx.setWaiter,
    selectedEventId: ctx.selectedEventId,
  }),
}))

vi.mock('@/composables/useStationPrintFailures', () => ({
  useStationPrintFailures: () => ({
    failedCount: ref(0),
    loadFailedJobs: vi.fn(),
  }),
}))

vi.mock('@/composables/useShiftSession', () => ({
  maybeEndShiftOnSwitch: ctx.maybeEndShiftOnSwitch,
}))

vi.mock('@/composables/usePiConnectivity', () => ({
  usePiConnectivity: () => ({
    status: ctx.status,
    probing: ctx.probing,
    unreachable: computed(() => ctx.status?.value === 'unreachable'),
    ensureReachable: ctx.ensureReachable,
    probeNow: vi.fn(async () => ctx.status?.value === 'reachable'),
  }),
}))

ctx.event = ref<EdgeBundleEvent | null>(null)
ctx.waiter = ref({ uuid: 'w-1', name: 'Anna' })
ctx.selectedEventId = ref(1)
ctx.status = ref<'unknown' | 'reachable' | 'unreachable'>('reachable')
ctx.probing = ref(false)

const { push, setWaiter, maybeEndShiftOnSwitch, ensureReachable } = ctx
const eventRef = ctx.event!
const waiterRef = ctx.waiter!
const selectedEventIdRef = ctx.selectedEventId!
const status = ctx.status!
const probing = ctx.probing!

import { isAndroidApp } from '@/api'
import WaiterHubView from './WaiterHubView.vue'

function baseEvent(statusValue: string, paymentTypes: string[] = ['cash']): EdgeBundleEvent {
  return {
    id: 1,
    name: 'Sommerfest',
    currency: 'CHF',
    payment_mode: 'pay_later',
    status: statusValue,
    payment_types: paymentTypes,
  } as EdgeBundleEvent
}

function bundleWithReaders(
  readers: { sumup_reader_id: string; label: string }[],
): EdgeBundleResponse {
  return {
    organisation_id: 1,
    events: [],
    sumup_readers: readers,
  } as unknown as EdgeBundleResponse
}

function mountHub() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/hub', name: 'hub', component: { template: '<div/>' } },
      { path: '/events', name: 'events', component: { template: '<div/>' } },
      { path: '/login', name: 'login', component: { template: '<div/>' } },
      { path: '/connection-setup', name: 'connection-setup', component: { template: '<div/>' } },
    ],
  })
  router.push = push
  return mount(WaiterHubView, { global: { plugins: [router] } })
}

async function clickHubButton(wrapper: ReturnType<typeof mountHub>, label: string) {
  const btn = wrapper.findAll('button').find((b) => b.text().includes(label))
  expect(btn).toBeTruthy()
  await btn!.trigger('click')
  await flushPromises()
}

describe('WaiterHubView', () => {
  beforeEach(() => {
    push.mockReset()
    setWaiter.mockReset()
    maybeEndShiftOnSwitch.mockReset()
    maybeEndShiftOnSwitch.mockResolvedValue(true)
    ensureReachable.mockReset()
    ensureReachable.mockResolvedValue(true)
    status.value = 'reachable'
    probing.value = false
    eventRef.value = baseEvent('test')
    waiterRef.value = { uuid: 'w-1', name: 'Anna' }
    selectedEventIdRef.value = 1
    store.bundle.value = null
    vi.mocked(isAndroidApp).mockReturnValue(false)
  })

  it('shows TESTBETRIEB pill when event status is test', async () => {
    const wrapper = mountHub()
    await flushPromises()
    const pill = wrapper.find('.test-pill')
    expect(pill.exists()).toBe(true)
    expect(pill.text()).toBe('TESTBETRIEB')
  })

  it('hides TESTBETRIEB pill when event status is prod', async () => {
    eventRef.value = baseEvent('prod')
    const wrapper = mountHub()
    await flushPromises()
    expect(wrapper.find('.test-pill').exists()).toBe(false)
  })

  it('shows Bluetooth tile on Android only when event enables Bluetooth printing', async () => {
    vi.mocked(isAndroidApp).mockReturnValue(true)
    eventRef.value = { ...baseEvent('test'), bluetooth_printing_enabled: true } as EdgeBundleEvent
    const wrapper = mountHub()
    await flushPromises()
    expect(wrapper.text()).toContain('Bluetooth Drucker')

    eventRef.value = { ...baseEvent('test'), bluetooth_printing_enabled: false } as EdgeBundleEvent
    const wrapperOff = mountHub()
    await flushPromises()
    expect(wrapperOff.text()).not.toContain('Bluetooth Drucker')
  })

  it('shows unreachable banner when Pi is unreachable', async () => {
    status.value = 'unreachable'
    const wrapper = mountHub()
    await flushPromises()
    expect(wrapper.text()).toContain('Keine Verbindung zur Kasse')
  })

  it('navigates money-path actions when ensureReachable succeeds', async () => {
    const wrapper = mountHub()
    await flushPromises()
    await clickHubButton(wrapper, 'Neue Bestellung')
    expect(push).toHaveBeenCalledWith({ name: 'table-new' })
    push.mockClear()

    await clickHubButton(wrapper, 'Tisch abrechnen')
    expect(push).toHaveBeenCalledWith({ name: 'table-settle-keypad' })
    push.mockClear()

    await clickHubButton(wrapper, 'Offene Tische')
    expect(push).toHaveBeenCalledWith({ name: 'tables-open' })
    push.mockClear()

    await clickHubButton(wrapper, 'Sammelrechnungen')
    expect(push).toHaveBeenCalledWith({ name: 'collective-open' })
    push.mockClear()

    await clickHubButton(wrapper, 'Lagerbestand')
    expect(push).toHaveBeenCalledWith({ name: 'stock' })
  })

  it('blocks money-path actions when ensureReachable fails', async () => {
    ensureReachable.mockResolvedValue(false)
    status.value = 'unreachable'
    const wrapper = mountHub()
    await flushPromises()
    for (const label of [
      'Neue Bestellung',
      'Tisch abrechnen',
      'Offene Tische',
      'Sammelrechnungen',
      'Lagerbestand',
    ]) {
      await clickHubButton(wrapper, label)
    }
    expect(push).not.toHaveBeenCalled()
    expect(ensureReachable).toHaveBeenCalled()
  })

  it('shows SumUp label and switch when bound with multiple readers', async () => {
    eventRef.value = baseEvent('test', ['cash', 'sumup_connected'])
    waiterRef.value = {
      uuid: 'w-1',
      name: 'Anna',
      sumupReaderId: 'r1',
      sumupReaderLabel: 'Bar',
    }
    store.bundle.value = bundleWithReaders([
      { sumup_reader_id: 'r1', label: 'Bar' },
      { sumup_reader_id: 'r2', label: 'Terrasse' },
    ])
    const wrapper = mountHub()
    await flushPromises()
    expect(wrapper.text()).toContain('SumUp: Bar')
    expect(wrapper.text()).toContain('SumUp-Gerät wechseln')
  })

  it('updates waiter session on device switch without shift end or login', async () => {
    eventRef.value = baseEvent('test', ['cash', 'sumup_connected'])
    waiterRef.value = {
      uuid: 'w-1',
      name: 'Anna',
      sumupReaderId: 'r1',
      sumupReaderLabel: 'Bar',
    }
    store.bundle.value = bundleWithReaders([
      { sumup_reader_id: 'r1', label: 'Bar' },
      { sumup_reader_id: 'r2', label: 'Terrasse' },
    ])
    const wrapper = mountHub()
    await flushPromises()

    await wrapper.get('button.sumup-switch-btn').trigger('click')
    const rows = wrapper.findAll('button.waiter-row')
    const terrasse = rows.find((r) => r.text().includes('Terrasse'))
    expect(terrasse).toBeTruthy()
    await terrasse!.trigger('click')

    expect(setWaiter).toHaveBeenCalledWith({
      uuid: 'w-1',
      name: 'Anna',
      sumupReaderId: 'r2',
      sumupReaderLabel: 'Terrasse',
    })
    expect(maybeEndShiftOnSwitch).not.toHaveBeenCalled()
    expect(push).not.toHaveBeenCalledWith({ name: 'login' })
  })

  it('hides switch with a single reader but still shows bound label', async () => {
    eventRef.value = baseEvent('test', ['cash', 'sumup_connected'])
    waiterRef.value = {
      uuid: 'w-1',
      name: 'Anna',
      sumupReaderId: 'r1',
      sumupReaderLabel: 'Bar',
    }
    store.bundle.value = bundleWithReaders([{ sumup_reader_id: 'r1', label: 'Bar' }])
    const wrapper = mountHub()
    await flushPromises()
    expect(wrapper.text()).toContain('SumUp: Bar')
    expect(wrapper.text()).not.toContain('SumUp-Gerät wechseln')
  })

  it('hides SumUp label and switch when sumup_connected is not enabled', async () => {
    eventRef.value = baseEvent('test', ['cash'])
    waiterRef.value = {
      uuid: 'w-1',
      name: 'Anna',
      sumupReaderId: 'r1',
      sumupReaderLabel: 'Bar',
    }
    store.bundle.value = bundleWithReaders([
      { sumup_reader_id: 'r1', label: 'Bar' },
      { sumup_reader_id: 'r2', label: 'Terrasse' },
    ])
    const wrapper = mountHub()
    await flushPromises()
    expect(wrapper.text()).not.toContain('SumUp: Bar')
    expect(wrapper.text()).not.toContain('SumUp-Gerät wechseln')
  })
})
