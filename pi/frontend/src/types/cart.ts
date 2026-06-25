import type { DiscountIn, LineAdditionIn } from '@/types/api'

/** Client-side cart line (UI state, not an API payload). */
export interface CartLine {
  lineId: string
  article_id?: number
  qty: number
  note?: string
  additions?: LineAdditionIn[]
  station_uuid?: string | null
  discount?: DiscountIn | null
  kind?: string
  voucher_definition_uuid?: string
  voucher_name?: string
  value_cents?: number
  unit_cents?: number
}

export interface VoucherBasketLine {
  voucher_definition_uuid: string
  qty: number
  note?: string
  additions?: LineAdditionIn[]
}

export interface ToastState {
  message: string
  type: 'ok' | 'err'
}

export interface WaiterSession {
  uuid: string
  name: string
}

export interface RegisterSession {
  uuid: string
  name: string
}
