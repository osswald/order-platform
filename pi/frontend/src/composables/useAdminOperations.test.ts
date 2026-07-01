import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import { bundleWithRegisters, defaultBundle } from '@tests/fixtures/bundle'
import type { EdgeBundleEvent } from '@/types/api'

const bundleRef = ref(defaultBundle())
const selectedEventIdRef = ref<number | null>(1)

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
    resolve: (loc: { name: string; params?: Record<string, string> }) => ({
      href: loc.params?.registerUuid
        ? `/register/${loc.params.registerUuid}/display`
        : `/kitchen/${loc.params?.printerSlug || 'station'}`,
    }),
    push: vi.fn(),
  }),
}))

import { useAdminOperations } from './useAdminOperations'

describe('useAdminOperations', () => {
  beforeEach(() => {
    bundleRef.value = defaultBundle()
    selectedEventIdRef.value = 1
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
})
