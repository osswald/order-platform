import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import type { KitchenOrderTicket, KitchenTicketLineEntry } from '@/types/api'
import {
  kitchenTicketActionBtnStyle,
  kitchenTicketActionsLayoutStyle,
} from '@/utils/kitchenTicketActionStyles'
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
} = {}) {
  const selectedQty = opts.selectedQty ?? (() => 0)
  return mount(KitchenTicketColumn, {
    props: {
      ticket: ticket(),
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
})
