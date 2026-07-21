import { describe, expect, it } from 'vitest'
import {
  kitchenTicketActionBtnStyle,
  kitchenTicketActionsLayoutStyle,
} from './kitchenTicketActionStyles'

describe('kitchenTicketActionStyles', () => {
  it('stacks actions vertically so long labels get full ticket width', () => {
    expect(kitchenTicketActionsLayoutStyle.display).toBe('flex')
    expect(kitchenTicketActionsLayoutStyle.flexDirection).toBe('column')
  })

  it('resets WebKit button chrome and uses full-width labels', () => {
    expect(kitchenTicketActionBtnStyle.width).toBe('100%')
    expect(kitchenTicketActionBtnStyle.minWidth).toBe('0')
    expect(kitchenTicketActionBtnStyle.whiteSpace).toBe('normal')
    expect(kitchenTicketActionBtnStyle.appearance).toBe('none')
    expect(kitchenTicketActionBtnStyle.WebkitAppearance).toBe('none')
  })
})
