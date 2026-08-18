/** Official MDI `table-chair` path (Material Design Icons 7.4.47). */
export const MDI_TABLE_CHAIR =
  'M12 22H6A2 2 0 0 1 8 20V8H2V5H16V8H10V20A2 2 0 0 1 12 22M22 2V22H20V15H15V22H13V14A2 2 0 0 1 15 12H20V2Z'

/** Official MDI `food-takeout-box` path (Material Design Icons 7.4.47). */
export const MDI_FOOD_TAKEOUT_BOX =
  'M5.26 11H18.74L18.07 20H5.93L5.26 11M9 4H14.97L19 7.38L20.59 5.79L22 7.21L19.21 10H4.79L2 7.21L3.41 5.8L5 7.38L9 4Z'

export const KITCHEN_TICKET_TYPE_TABLE_COLOR = '#38bdf8'
export const KITCHEN_TICKET_TYPE_PICKUP_COLOR = '#c084fc'

export type KitchenTicketFulfillmentType = 'table' | 'pickup'

interface KitchenTicketTypeInput {
  pickup_code?: unknown
  [key: string]: unknown
}

export function kitchenTicketFulfillmentType(ticket: KitchenTicketTypeInput): KitchenTicketFulfillmentType {
  return ticket.pickup_code ? 'pickup' : 'table'
}

export function kitchenTicketTypeChrome(ticket: KitchenTicketTypeInput): {
  type: KitchenTicketFulfillmentType
  path: string
  color: string
} {
  const type = kitchenTicketFulfillmentType(ticket)
  if (type === 'pickup') {
    return { type, path: MDI_FOOD_TAKEOUT_BOX, color: KITCHEN_TICKET_TYPE_PICKUP_COLOR }
  }
  return { type, path: MDI_TABLE_CHAIR, color: KITCHEN_TICKET_TYPE_TABLE_COLOR }
}
