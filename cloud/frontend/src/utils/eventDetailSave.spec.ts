import { describe, expect, it } from 'vitest'
import {
  resolveEventStammdatenSaveNavigation,
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
