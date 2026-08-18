import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import type { KitchenOrderTicket, KitchenTicketLineEntry } from '@/types/api'
import {
  KITCHEN_MIN_COLUMN_WIDTH_PX,
  KITCHEN_ORDER_GAP_PX,
} from '@/utils/kitchenMonitorHelpers'
import {
  kitchenTicketActionBtnStyle,
  kitchenTicketActionsLayoutStyle,
} from '@/utils/kitchenTicketActionStyles'
import {
  KITCHEN_TICKET_TYPE_PICKUP_COLOR,
  KITCHEN_TICKET_TYPE_TABLE_COLOR,
  MDI_FOOD_TAKEOUT_BOX,
  MDI_TABLE_CHAIR,
} from '@/utils/kitchenTicketType'
import KitchenTicketColumn from './KitchenTicketColumn.vue'

function line(overrides: Partial<KitchenTicketLineEntry> = {}): KitchenTicketLineEntry {
  return {
    id: 1,
    line_index: 0,
    line: { article_id: 10, qty: 2, note: '', additions: [] },
    qty_total: 2,
    qty_printed: 0,
    qty_remaining: 2,
    ...overrides,
  }
}

function ticket(overrides: Partial<KitchenOrderTicket> = {}): KitchenOrderTicket {
  return {
    id: 42,
    local_order_id: 7,
    event_id: 1,
    station_uuid: 'station-1',
    status: 'open',
    order_number: 7,
    table_number: 12,
    lines: [line()],
    ...overrides,
  } as KitchenOrderTicket
}

function mountColumn(opts: {
  selectedQty?: (lineId: number) => number
  busy?: boolean
  ticket?: KitchenOrderTicket
} = {}) {
  const selectedQty = opts.selectedQty ?? (() => 0)
  return mount(KitchenTicketColumn, {
    props: {
      ticket: opts.ticket ?? ticket(),
      event: null,
      busy: opts.busy ?? false,
      selectedQty,
    },
  })
}

describe('KitchenTicketColumn', () => {
  it('renders Teildruck and Komplettdruck labels inside action spans', () => {
    const wrapper = mountColumn()
    expect(wrapper.find('.partial-btn .action-label').text()).toBe('Teildruck')
    expect(wrapper.find('.complete-btn .action-label').text()).toBe('Komplettdruck')
  })

  it('disables Teildruck without selection and enables it when a line is selected', () => {
    const none = mountColumn({ selectedQty: () => 0 })
    expect(none.find('.partial-btn').attributes('disabled')).toBeDefined()
    expect(none.find('.complete-btn').attributes('disabled')).toBeUndefined()

    const some = mountColumn({ selectedQty: (id) => (id === 1 ? 1 : 0) })
    expect(some.find('.partial-btn').attributes('disabled')).toBeUndefined()
    expect(some.find('.complete-btn').attributes('disabled')).toBeUndefined()
  })

  it('emits partialPrint and completePrint on action clicks', async () => {
    const wrapper = mountColumn({ selectedQty: () => 1 })
    await wrapper.find('.partial-btn').trigger('click')
    await wrapper.find('.complete-btn').trigger('click')
    expect(wrapper.emitted('partialPrint')).toHaveLength(1)
    expect(wrapper.emitted('completePrint')).toHaveLength(1)
  })

  it('stacks Safari-safe full-width action buttons', () => {
    const wrapper = mountColumn()
    const actionsStyle = wrapper.find('.ticket-actions').attributes('style') || ''
    expect(actionsStyle).toContain(kitchenTicketActionsLayoutStyle.flexDirection)

    const btnStyle = wrapper.find('.action-btn').attributes('style') || ''
    expect(btnStyle).toContain(`width: ${kitchenTicketActionBtnStyle.width}`)
    expect(btnStyle).toContain(`min-width: ${kitchenTicketActionBtnStyle.minWidth}`)
  })

  it('prefers article labels for line names', () => {
    const wrapper = mount(KitchenTicketColumn, {
      props: {
        ticket: ticket({
          lines: [
            line({
              line: {
                article_id: 10,
                qty: 1,
                note: '',
                article_name: 'Burger Deluxe',
                additions: [{ article_id: 30, qty: 1, name: 'mit Salat' }],
              } as never,
            }),
          ],
        }),
        event: {
          articles: {
            '10': { id: 10, name: 'Burger Deluxe', label: 'Burger', price: 12, additions: [] },
            '30': { id: 30, name: 'mit Salat', label: 'Salat', price: 2, additions: [] },
          },
        } as never,
        busy: false,
        selectedQty: () => 0,
      },
    })
    expect(wrapper.text()).toContain('Burger')
    expect(wrapper.text()).toContain('+ 1x Salat')
    expect(wrapper.text()).not.toContain('Burger Deluxe')
  })

  it('shows a sky table-chair icon on the title line for table tickets', () => {
    const wrapper = mountColumn()
    expect(wrapper.find('.ticket-title').text()).toContain('Tisch 12')
    const icon = wrapper.find('.ticket-type-icon')
    expect(icon.exists()).toBe(true)
    expect(icon.classes()).toContain('ticket-type-icon--table')
    expect(icon.find('path').attributes('d')).toBe(MDI_TABLE_CHAIR)
    expect(icon.attributes('style') || '').toContain(KITCHEN_TICKET_TYPE_TABLE_COLOR)
    expect(wrapper.find('.elapsed').attributes('style') || '').not.toContain(KITCHEN_TICKET_TYPE_TABLE_COLOR)
  })

  it('shows a violet takeout-box icon on the title line for pickup tickets', () => {
    const wrapper = mountColumn({ ticket: ticket({ pickup_code: 'A1', table_number: null }) })
    expect(wrapper.find('.ticket-title').text()).toContain('Pickup A1')
    const icon = wrapper.find('.ticket-type-icon')
    expect(icon.classes()).toContain('ticket-type-icon--pickup')
    expect(icon.find('path').attributes('d')).toBe(MDI_FOOD_TAKEOUT_BOX)
    expect(icon.attributes('style') || '').toContain(KITCHEN_TICKET_TYPE_PICKUP_COLOR)
  })

  it('keeps ticket header padding and column-gap layout constants unchanged', () => {
    expect(KITCHEN_ORDER_GAP_PX).toBe(6)
    expect(KITCHEN_MIN_COLUMN_WIDTH_PX).toBe(200)
    const src = readFileSync(join(dirname(fileURLToPath(import.meta.url)), 'KitchenTicketColumn.vue'), 'utf8')
    expect(src).toContain('padding: 0.7rem 0.85rem 0.6rem;')
    const wrapper = mountColumn()
    expect(wrapper.find('.ticket-title-row').exists()).toBe(true)
    expect(wrapper.findAll('.ticket-header')).toHaveLength(1)
  })
})
