import { describe, expect, it } from 'vitest'
import {
  KITCHEN_TICKET_TYPE_PICKUP_COLOR,
  KITCHEN_TICKET_TYPE_TABLE_COLOR,
  MDI_FOOD_TAKEOUT_BOX,
  MDI_TABLE_CHAIR,
  kitchenTicketFulfillmentType,
  kitchenTicketTypeChrome,
} from './kitchenTicketType'

describe('kitchenTicketFulfillmentType', () => {
  it('treats a present pickup code as pickup', () => {
    expect(kitchenTicketFulfillmentType({ pickup_code: 'A1' })).toBe('pickup')
  })

  it('treats missing pickup code as table', () => {
    expect(kitchenTicketFulfillmentType({})).toBe('table')
    expect(kitchenTicketFulfillmentType({ pickup_code: null })).toBe('table')
    expect(kitchenTicketFulfillmentType({ pickup_code: '' })).toBe('table')
  })
})

describe('kitchenTicketTypeChrome', () => {
  it('returns the table-chair path and sky color for table tickets', () => {
    expect(kitchenTicketTypeChrome({})).toEqual({
      type: 'table',
      path: MDI_TABLE_CHAIR,
      color: KITCHEN_TICKET_TYPE_TABLE_COLOR,
    })
    expect(KITCHEN_TICKET_TYPE_TABLE_COLOR).toBe('#38bdf8')
  })

  it('returns the takeout-box path and violet color for pickup tickets', () => {
    expect(kitchenTicketTypeChrome({ pickup_code: 'A1' })).toEqual({
      type: 'pickup',
      path: MDI_FOOD_TAKEOUT_BOX,
      color: KITCHEN_TICKET_TYPE_PICKUP_COLOR,
    })
    expect(KITCHEN_TICKET_TYPE_PICKUP_COLOR).toBe('#c084fc')
  })
})
