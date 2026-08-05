import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import { bundleWithRegisters, defaultBundle } from '@tests/fixtures/bundle'
import type { EdgeBundleEvent } from '@/types/api'
import { setApiBase } from '@/api/base'

const bundleRef = ref(defaultBundle())
const selectedEventIdRef = ref<number | null>(1)
const routerPush = vi.fn()
const windowOpen = vi.fn()

vi.mock('@/composables/useBundle', () => ({
  useBundle: () => ({
    bundle: bundleRef,
    busy: ref(false),
    showToast: vi.fn(),
    selectedEventId: selectedEventIdRef,
  }),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({
    resolve: (loc: {
      name: string
      params?: Record<string, string>
      query?: Record<string, string>
    }) => {
      const query = loc.query?.event ? `?event=${loc.query.event}` : ''
      if (loc.params?.registerUuid) {
        return { href: `/register/${loc.params.registerUuid}/display${query}` }
      }
      if (loc.name === 'pickup') {
        return { href: `/pickup${query}` }
      }
      return { href: `/kitchen/${loc.params?.printerSlug || 'station'}${query}` }
    },
    push: routerPush,
  }),
}))

import { useAdminOperations } from './useAdminOperations'

function bundleWithKitchenMonitors() {
  const b = defaultBundle()
  const ev = b.events![0]
  ev.kitchen_monitors_enabled = true
  ev.configuration = {
    ...ev.configuration,
    kitchen_monitors: [{ printer_appliance_id: 101, label: 'Grill', sort_order: 0 }],
  }
  return b
}

describe('useAdminOperations', () => {
  beforeEach(() => {
    bundleRef.value = defaultBundle()
    selectedEventIdRef.value = 1
    routerPush.mockReset()
    windowOpen.mockReset()
    vi.stubGlobal('open', windowOpen)
    vi.unstubAllEnvs()
    localStorage.clear()
    setApiBase('http://192.168.192.10')
    vi.stubGlobal('location', { origin: 'http://192.168.192.10' })
  })

  it('hides event select when only one event is available', () => {
    const events = bundleRef.value.events as EdgeBundleEvent[]
    bundleRef.value = { ...defaultBundle(), events: [events[0]] }
    const { showEventSelect, singleEventName } = useAdminOperations()
    expect(showEventSelect.value).toBe(false)
    expect(singleEventName.value).toBeTruthy()
  })

  it('shows event select when multiple events are available', () => {
    const events = bundleRef.value.events as EdgeBundleEvent[]
    bundleRef.value = {
      ...defaultBundle(),
      events: [
        events[0],
        { ...events[0], id: 2, name: 'Zweites Event' },
      ],
    }
    const { showEventSelect } = useAdminOperations()
    expect(showEventSelect.value).toBe(true)
  })

  it('hides register select when only one cash register is available', () => {
    bundleRef.value = bundleWithRegisters()
    const { showRegisterSelect } = useAdminOperations()
    expect(showRegisterSelect.value).toBe(false)
  })

  it('shows register select when multiple cash registers are available', () => {
    const base = bundleWithRegisters()
    const ev = base.events![0]
    ev.configuration = {
      ...ev.configuration,
      cash_registers: [
        { uuid: 'register-1', name: 'Kasse 1' },
        { uuid: 'register-2', name: 'Kasse 2' },
      ],
    }
    bundleRef.value = base
    const { showRegisterSelect } = useAdminOperations()
    expect(showRegisterSelect.value).toBe(true)
  })

  it('exposes single register name when only one cash register exists', () => {
    bundleRef.value = bundleWithRegisters()
    const { singleRegisterName, hasCashRegisters } = useAdminOperations()
    expect(hasCashRegisters.value).toBe(true)
    expect(singleRegisterName.value).toBe('Kasse 1')
  })

  it('includes ops event id in kitchen monitor URLs', () => {
    bundleRef.value = bundleWithKitchenMonitors()
    const { kitchenMonitorRows, opsEventId } = useAdminOperations()
    expect(opsEventId.value).toBe(1)
    expect(kitchenMonitorRows.value.length).toBeGreaterThan(0)
    expect(kitchenMonitorRows.value[0].url).toContain('event=1')
    expect(kitchenMonitorRows.value[0].url).toMatch(/\/kitchen\/[^/?]+/)
  })

  it('includes ops event id in register display URL', () => {
    bundleRef.value = bundleWithRegisters()
    const { displayUrl, opsEventId } = useAdminOperations()
    expect(opsEventId.value).toBe(1)
    expect(displayUrl.value).toContain('/register/register-1/display')
    expect(displayUrl.value).toContain('event=1')
  })

  it('uses Pi API base for kitchen URLs on Android (not appassets)', () => {
    vi.stubEnv('VITE_ANDROID_APP', 'true')
    vi.stubGlobal('location', { origin: 'https://appassets.androidplatform.net' })
    setApiBase('http://192.168.192.10')
    bundleRef.value = bundleWithKitchenMonitors()
    const { kitchenMonitorRows } = useAdminOperations()
    expect(kitchenMonitorRows.value[0].url).toMatch(/^http:\/\/192\.168\.192\.10\/kitchen\//)
    expect(kitchenMonitorRows.value[0].url).toContain('event=1')
    expect(kitchenMonitorRows.value[0].url).not.toContain('appassets')
  })

  it('opens kitchen via router.push on Android', () => {
    vi.stubEnv('VITE_ANDROID_APP', 'true')
    bundleRef.value = bundleWithKitchenMonitors()
    const { openKitchen, opsEventId } = useAdminOperations()
    openKitchen('grill')
    expect(opsEventId.value).toBe(1)
    expect(routerPush).toHaveBeenCalledWith({
      name: 'kitchen',
      params: { printerSlug: 'grill' },
      query: { event: '1' },
    })
    expect(windowOpen).not.toHaveBeenCalled()
  })

  it('opens kitchen via window.open when not Android', () => {
    bundleRef.value = bundleWithKitchenMonitors()
    const { openKitchen } = useAdminOperations()
    openKitchen('grill')
    expect(windowOpen).toHaveBeenCalled()
    expect(routerPush).not.toHaveBeenCalled()
  })

  it('opens customer display via router.push on Android', () => {
    vi.stubEnv('VITE_ANDROID_APP', 'true')
    bundleRef.value = bundleWithRegisters()
    const { openDisplay } = useAdminOperations()
    openDisplay()
    expect(routerPush).toHaveBeenCalledWith({
      name: 'register-display',
      params: { registerUuid: 'register-1' },
      query: { event: '1' },
    })
    expect(windowOpen).not.toHaveBeenCalled()
  })
})
