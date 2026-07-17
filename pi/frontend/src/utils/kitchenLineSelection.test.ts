import { describe, expect, it } from 'vitest'
import type { KitchenTicketLineEntry } from '@/types/api'
import {
  capSelectionToLines,
  cycleLineSelection,
  hasTicketSelection,
  lineSelectionLabel,
  selectionPayloadForTicket,
} from './kitchenLineSelection'

function line(overrides: Partial<KitchenTicketLineEntry> = {}): KitchenTicketLineEntry {
  return {
    id: 1,
    line_index: 0,
    line: { article_id: 10, qty: 5, note: '', additions: [] },
    qty_total: 5,
    qty_printed: 0,
    qty_remaining: 5,
    ...overrides,
  }
}

describe('cycleLineSelection', () => {
  it('cycles from 0 through remaining back to 0', () => {
    const entry = line()
    expect(cycleLineSelection(entry, 0)).toBe(1)
    expect(cycleLineSelection(entry, 1)).toBe(2)
    expect(cycleLineSelection(entry, 5)).toBe(0)
  })
})

describe('lineSelectionLabel', () => {
  it('shows fraction when selected', () => {
    expect(lineSelectionLabel(line(), 2, 'Schnitzel')).toBe('2/5 Schnitzel')
  })

  it('shows remaining qty when unselected', () => {
    expect(lineSelectionLabel(line(), 0, 'Schnitzel')).toBe('5 Schnitzel')
  })
})

describe('selectionPayloadForTicket', () => {
  it('returns only lines with selected qty', () => {
    const lines = [line({ id: 1 }), line({ id: 2, qty_remaining: 3 })]
    const payload = selectionPayloadForTicket(lines, { 1: 2, 2: 0 })
    expect(payload).toEqual([{ line_id: 1, qty: 2 }])
  })
})

describe('hasTicketSelection', () => {
  it('detects any selected line on ticket', () => {
    expect(hasTicketSelection([1, 2], { 2: 1 })).toBe(true)
    expect(hasTicketSelection([1, 2], {})).toBe(false)
  })
})

describe('capSelectionToLines', () => {
  it('caps selection to current remaining qty', () => {
    const lines = [line({ id: 1, qty_remaining: 2 })]
    expect(capSelectionToLines({ 1: 5 }, lines)).toEqual({ 1: 2 })
  })
})
