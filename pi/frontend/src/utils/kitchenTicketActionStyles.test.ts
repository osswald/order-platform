import { describe, expect, it } from 'vitest'
import {
  kitchenTicketActionBtnStyle,
  kitchenTicketActionsGridTemplateColumns,
} from './kitchenTicketActionStyles'

describe('kitchenTicketActionStyles', () => {
  it('uses shrink-friendly two-column tracks', () => {
    expect(kitchenTicketActionsGridTemplateColumns).toBe('minmax(0, 1fr) minmax(0, 1fr)')
  })

  it('allows action buttons to shrink and wrap', () => {
    expect(kitchenTicketActionBtnStyle.minWidth).toBe('0')
    expect(kitchenTicketActionBtnStyle.whiteSpace).toBe('normal')
    expect(kitchenTicketActionBtnStyle.appearance).toBe('none')
    expect(kitchenTicketActionBtnStyle.WebkitAppearance).toBe('none')
  })
})
