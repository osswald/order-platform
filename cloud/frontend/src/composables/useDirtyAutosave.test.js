import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, nextTick, ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { useDirtyAutosave } from './useDirtyAutosave'

function mountAutosave(options) {
  let result
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
})
