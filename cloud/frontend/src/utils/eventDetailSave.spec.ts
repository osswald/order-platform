import { describe, expect, it } from 'vitest'
import {
  eventConfigurationAutosaveSnapshot,
  pickupPrefixModeOnlyUpdatePayload,
  resolveEventStammdatenSaveNavigation,
  stammdatenBaselineAfterPickupPrefixModeSave,
  stammdatenBaselineAfterStatusSave,
  statusOnlyUpdatePayload,
} from './eventDetailSave'

describe('eventDetailSave', () => {
  it('builds a status-only update payload', () => {
    expect(statusOnlyUpdatePayload('prod')).toEqual({ status: 'prod' })
    expect(Object.keys(statusOnlyUpdatePayload('test'))).toEqual(['status'])
  })

  it('updates only status in the stammdaten baseline JSON', () => {
    const baseline = JSON.stringify({
      name: 'Sommerfest',
      status: 'test',
      start: '2026-01-01T00:00:00.000Z',
      paymentTypes: ['cash'],
    })
    const next = stammdatenBaselineAfterStatusSave(baseline, 'prod')
    const parsed = JSON.parse(next)
    expect(parsed.status).toBe('prod')
    expect(parsed.name).toBe('Sommerfest')
    expect(parsed.paymentTypes).toEqual(['cash'])
  })

  it('builds a pickup-prefix-mode-only update payload', () => {
    expect(pickupPrefixModeOnlyUpdatePayload('station')).toEqual({
      pickup_prefix_mode: 'station',
    })
    expect(Object.keys(pickupPrefixModeOnlyUpdatePayload('register'))).toEqual([
      'pickup_prefix_mode',
    ])
  })

  it('updates only pickupPrefixMode in the stammdaten baseline JSON', () => {
    const baseline = JSON.stringify({
      name: 'Sommerfest',
      status: 'config',
      pickupPrefixMode: 'register',
      paymentTypes: ['cash'],
    })
    const next = stammdatenBaselineAfterPickupPrefixModeSave(baseline, 'station')
    const parsed = JSON.parse(next)
    expect(parsed.pickupPrefixMode).toBe('station')
    expect(parsed.name).toBe('Sommerfest')
    expect(parsed.status).toBe('config')
  })

  it('includes pickup prefix mode in the configuration autosave snapshot', () => {
    const before = eventConfigurationAutosaveSnapshot({
      pickupPrefixMode: 'register',
      configuration: { stations: [{ pickup_code_prefix: null }] },
    })
    const afterMode = eventConfigurationAutosaveSnapshot({
      pickupPrefixMode: 'station',
      configuration: { stations: [{ pickup_code_prefix: null }] },
    })
    const afterLetters = eventConfigurationAutosaveSnapshot({
      pickupPrefixMode: 'station',
      configuration: { stations: [{ pickup_code_prefix: 'G' }] },
    })
    expect(JSON.stringify(before)).not.toBe(JSON.stringify(afterMode))
    expect(JSON.stringify(afterMode)).not.toBe(JSON.stringify(afterLetters))
    expect(afterLetters.configuration).toEqual({
      stations: [{ pickup_code_prefix: 'G' }],
    })
  })

  it('stays on detail after edit save', () => {
    expect(resolveEventStammdatenSaveNavigation('edit')).toEqual({ kind: 'stay' })
  })

  it('navigates to new detail after create save', () => {
    expect(resolveEventStammdatenSaveNavigation('create', 42)).toEqual({
      kind: 'goToDetail',
      id: 42,
    })
  })
})
