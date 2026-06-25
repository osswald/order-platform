import { describe, expect, it } from 'vitest'
import {
  EVENT_STATUS_ORDER,
  eventStatusColor,
  eventStatusIndex,
  type EventStatusKey,
} from './eventStatus'

describe('EVENT_STATUS_ORDER', () => {
  it('lists lifecycle statuses in order', () => {
    expect(EVENT_STATUS_ORDER).toEqual(['config', 'test', 'prod', 'archive'])
  })
})

describe('eventStatusColor', () => {
  it('maps known statuses to Vuetify colors', () => {
    expect(eventStatusColor('config')).toBeUndefined()
    expect(eventStatusColor('test')).toBe('info')
    expect(eventStatusColor('prod')).toBe('success')
    expect(eventStatusColor('archive')).toBe('warning')
  })

  it('normalizes case', () => {
    expect(eventStatusColor('PROD')).toBe('success')
  })

  it('returns undefined for unknown statuses', () => {
    expect(eventStatusColor('unknown')).toBeUndefined()
  })
})

describe('eventStatusIndex', () => {
  it('returns index for known statuses', () => {
    const keys: EventStatusKey[] = ['config', 'test', 'prod', 'archive']
    keys.forEach((key, index) => {
      expect(eventStatusIndex(key)).toBe(index)
    })
  })

  it('returns -1 for unknown statuses', () => {
    expect(eventStatusIndex('unknown')).toBe(-1)
  })
})
