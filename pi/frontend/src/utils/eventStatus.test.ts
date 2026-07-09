import { describe, expect, it } from 'vitest'
import { eventStatusLabel, isEventTest } from './eventStatus'

describe('isEventTest', () => {
  it('returns true for test status', () => {
    expect(isEventTest('test')).toBe(true)
    expect(isEventTest('TEST')).toBe(true)
  })

  it('returns false for non-test statuses', () => {
    expect(isEventTest('prod')).toBe(false)
    expect(isEventTest('config')).toBe(false)
    expect(isEventTest('')).toBe(false)
    expect(isEventTest(null)).toBe(false)
    expect(isEventTest(undefined)).toBe(false)
  })
})

describe('eventStatusLabel', () => {
  it('maps known statuses', () => {
    expect(eventStatusLabel('test')).toBe('Testbetrieb')
    expect(eventStatusLabel('prod')).toBe('Produktivbetrieb')
  })
})
