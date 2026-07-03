import { afterEach, describe, expect, it, vi } from 'vitest'
import { isUuid, newUuid } from './newUuid'

describe('newUuid', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('returns a UUID v4 string', () => {
    expect(isUuid(newUuid())).toBe(true)
  })

  it('uses getRandomValues when randomUUID is unavailable', () => {
    const getRandomValues = vi.fn((array: Uint8Array) => {
      for (let index = 0; index < array.length; index += 1) {
        array[index] = index
      }
      return array
    })
    vi.stubGlobal('crypto', { getRandomValues })

    expect(isUuid(newUuid())).toBe(true)
    expect(getRandomValues).toHaveBeenCalled()
  })
})
