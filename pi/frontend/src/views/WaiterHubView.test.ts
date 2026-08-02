import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { computed, ref } from 'vue'
import type { EdgeBundleEvent } from '@/types/api'

const push = vi.fn()
const eventRef = ref<EdgeBundleEvent | null>(null)
const waiterRef = ref({ uuid: 'w-1', name: 'Anna' })
const selectedEventIdRef = ref(1)
const ensureReachable = vi.fn(async () => true)
const status = ref<'unknown' | 'reachable' | 'unreachable'>('reachable')
const probing = ref(false)

vi.mock('@/api', () => ({
  isAndroidApp: vi.fn(() => false),
}))

vi.mock('@/composables/useEventContext', () => ({
  useEventContext: () => ({
    event: eventRef,
    waiter: waiterRef,
    setWaiter: vi.fn(),
    selectedEventId: selectedEventIdRef,
  }),
}))

vi.mock('@/composables/useStationPrintFailures', () => ({
  useStationPrintFailures: () => ({
    failedCount: ref(0),
    loadFailedJobs: vi.fn(),
  }),
}))

vi.mock('@/composables/useShiftSession', () => ({
  maybeEndShiftOnSwitch: vi.fn(async () => true),
}))

vi.mock('@/composables/usePiConnectivity', () => ({
  usePiConnectivity: () => ({
    status,
    probing,
    unreachable: computed(() => status.value === 'unreachable'),
    ensureReachable,
    probeNow: vi.fn(async () => status.value === 'reachable'),
  }),
}))

import { isAndroidApp } from '@/api'
import WaiterHubView from './WaiterHubView.vue'

function baseEvent(statusValue: string): EdgeBundleEvent {
  return {
    id: 1,
    name: 'Sommerfest',
    currency: 'CHF',
    payment_mode: 'pay_later',
    status: statusValue,
  } as EdgeBundleEvent
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
    ensureReachable.mockReset()
    ensureReachable.mockResolvedValue(true)
    status.value = 'reachable'
    probing.value = false
    eventRef.value = baseEvent('test')
    waiterRef.value = { uuid: 'w-1', name: 'Anna' }
    selectedEventIdRef.value = 1
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
})
