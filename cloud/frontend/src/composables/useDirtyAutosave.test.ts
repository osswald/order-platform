import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, nextTick, ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { useDirtyAutosave } from './useDirtyAutosave'

function mountAutosave(options: Parameters<typeof useDirtyAutosave>[0]) {
  let result!: ReturnType<typeof useDirtyAutosave>
  const Comp = defineComponent({
    setup() {
      result = useDirtyAutosave(options)
      return () => null
    },
  })
  mount(Comp)
  return result
}

describe('useDirtyAutosave', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  it('marks dirty when watch source changes after initial snapshot', async () => {
    const state = ref({ name: 'A' })
    const saveFn = vi.fn(async () => true)
    const api = mountAutosave({
      getSnapshot: () => state.value,
      saveFn,
      watchSource: state,
      enabled: true,
    })

    api.markSaved()
    expect(api.status.value).toBe('saved')

    state.value = { name: 'B' }
    await nextTick()
    expect(api.isDirty.value).toBe(true)
    expect(api.status.value).toBe('dirty')
  })

  it('debounces save and calls saveFn on success', async () => {
    const state = ref({ count: 1 })
    const saveFn = vi.fn(async () => true)
    const api = mountAutosave({
      getSnapshot: () => state.value,
      saveFn,
      watchSource: state,
      enabled: true,
      debounceMs: 200,
    })

    api.markSaved()
    state.value = { count: 2 }
    await nextTick()

    vi.advanceTimersByTime(200)
    await flushPromises()

    expect(saveFn).toHaveBeenCalledTimes(1)
    expect(api.status.value).toBe('saved')
  })

  it('does not autosave when only an unwatched snapshot field changes', async () => {
    const watched = ref({ stations: [] as string[] })
    const unwatched = ref({ kitchenMonitors: [] as number[] })
    const saveFn = vi.fn(async () => true)
    const api = mountAutosave({
      getSnapshot: () => ({ ...watched.value, ...unwatched.value }),
      saveFn,
      watchSource: watched,
      enabled: true,
      debounceMs: 200,
    })

    api.markSaved()
    unwatched.value = { kitchenMonitors: [42] }
    await nextTick()

    expect(api.isDirty.value).toBe(true)
    expect(api.status.value).toBe('dirty')

    vi.advanceTimersByTime(200)
    await flushPromises()

    expect(saveFn).not.toHaveBeenCalled()
  })

  it('blocks save when validate returns an error message', async () => {
    const state = ref({ ok: true })
    const saveFn = vi.fn(async () => true)
    const api = mountAutosave({
      getSnapshot: () => state.value,
      saveFn,
      watchSource: state,
      enabled: true,
      validate: () => 'validation failed',
    })

    api.markSaved()
    state.value = { ok: false }
    await nextTick()
    vi.advanceTimersByTime(1000)
    await flushPromises()

    expect(saveFn).not.toHaveBeenCalled()
    expect(api.errorMessage.value).toBe('validation failed')
  })

  it('resumes save when enabled flips false→true while dirty without a further edit', async () => {
    const state = ref({ count: 1 })
    const enabled = ref(true)
    const saveFn = vi.fn(async () => true)
    const api = mountAutosave({
      getSnapshot: () => state.value,
      saveFn,
      watchSource: state,
      enabled,
      debounceMs: 200,
    })

    api.markSaved()
    enabled.value = false
    await nextTick()

    state.value = { count: 2 }
    await nextTick()
    expect(api.isDirty.value).toBe(true)

    vi.advanceTimersByTime(200)
    await flushPromises()
    expect(saveFn).not.toHaveBeenCalled()

    enabled.value = true
    await nextTick()
    vi.advanceTimersByTime(200)
    await flushPromises()

    expect(saveFn).toHaveBeenCalledTimes(1)
    expect(api.status.value).toBe('saved')
  })

  it('still debounces and coalesces rapid edits while enabled', async () => {
    const state = ref({ count: 1 })
    const saveFn = vi.fn(async () => true)
    const api = mountAutosave({
      getSnapshot: () => state.value,
      saveFn,
      watchSource: state,
      enabled: true,
      debounceMs: 200,
    })

    api.markSaved()
    state.value = { count: 2 }
    await nextTick()
    state.value = { count: 3 }
    await nextTick()
    state.value = { count: 4 }
    await nextTick()

    vi.advanceTimersByTime(199)
    await flushPromises()
    expect(saveFn).not.toHaveBeenCalled()

    vi.advanceTimersByTime(1)
    await flushPromises()

    expect(saveFn).toHaveBeenCalledTimes(1)
    expect(api.status.value).toBe('saved')
  })
})
