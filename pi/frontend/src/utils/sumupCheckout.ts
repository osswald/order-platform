import { api } from '@/api'
import type { EdgeBundleEvent, PaymentIn } from '@/types/api'
import { bundle } from '@/store/bundle'
import { registerSession, waiter } from '@/store/sessions'
import { buildSumupConnectedPayment, type SumupReceiptInfo } from './paymentTypes'
import {
  findSumupReaderLabel,
  getBundleSumupReaders,
  resolveRegisterSumupReaderId,
} from './sumupReaders'

const POLL_MS = 2000
const TIMEOUT_MS = 120_000

interface SumupCheckoutResponse {
  checkout_id: string
  status: string
  transaction_id?: string | null
  receipt_info?: SumupReceiptInfo | null
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export function resolveActiveSumupReaderId(event: EdgeBundleEvent): string {
  const readers = getBundleSumupReaders(bundle.value)
  const waiterReaderId = waiter.value?.sumupReaderId?.trim()
  if (waiterReaderId) return waiterReaderId

  const registerReaderId = resolveRegisterSumupReaderId(event, registerSession.value?.uuid)
  if (registerReaderId) return registerReaderId

  if (readers.length === 1) return readers[0].sumup_reader_id

  throw new Error('Kein SumUp-Gerät ausgewählt.')
}

export async function createSumupCheckout(input: {
  eventId: number
  amountCents: number
  currency: string
  readerId: string
  clientOrderId?: string | null
}): Promise<SumupCheckoutResponse> {
  return api<SumupCheckoutResponse>('/v1/sumup/checkout', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      event_id: input.eventId,
      amount_cents: input.amountCents,
      currency: input.currency,
      reader_id: input.readerId,
      client_order_id: input.clientOrderId || undefined,
      waiter_uuid: waiter.value?.uuid || undefined,
    }),
  })
}

export async function getSumupCheckoutStatus(eventId: number, checkoutId: string): Promise<SumupCheckoutResponse> {
  const params = new URLSearchParams({
    event_id: String(eventId),
    checkout_id: checkoutId,
  })
  return api<SumupCheckoutResponse>(`/v1/sumup/status?${params.toString()}`)
}

export async function terminateSumupCheckout(eventId: number, readerId: string): Promise<void> {
  await api('/v1/sumup/terminate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ event_id: eventId, reader_id: readerId }),
  })
}

async function pollSumupCheckoutUntilDone(
  eventId: number,
  checkoutId: string,
): Promise<SumupCheckoutResponse> {
  const deadline = Date.now() + TIMEOUT_MS
  while (Date.now() < deadline) {
    const status = await getSumupCheckoutStatus(eventId, checkoutId)
    if (status.status === 'paid' && status.transaction_id) {
      return status
    }
    if (status.status === 'failed' || status.status === 'terminated') {
      throw new Error('SumUp-Zahlung fehlgeschlagen oder abgebrochen.')
    }
    await sleep(POLL_MS)
  }
  throw new Error('SumUp-Zahlung: Zeitüberschreitung.')
}

export async function collectSumupConnectedPayment(input: {
  event: EdgeBundleEvent
  amountCents: number
  clientOrderId?: string | null
}): Promise<PaymentIn> {
  const readerId = resolveActiveSumupReaderId(input.event)
  const readers = getBundleSumupReaders(bundle.value)
  const readerLabel = findSumupReaderLabel(readers, readerId)
  if (!readerLabel && readers.length > 1) {
    throw new Error('Kein SumUp-Gerät ausgewählt.')
  }

  const created = await createSumupCheckout({
    eventId: input.event.id,
    amountCents: input.amountCents,
    currency: input.event.currency,
    readerId,
    clientOrderId: input.clientOrderId,
  })

  try {
    const finalStatus = await pollSumupCheckoutUntilDone(input.event.id, created.checkout_id)
    const payment = buildSumupConnectedPayment(
      input.amountCents,
      finalStatus.transaction_id || '',
      finalStatus.receipt_info,
    )[0]
    if (!payment.sumup_transaction_id) {
      throw new Error('SumUp-Transaktion ohne ID.')
    }
    return payment
  } catch (err) {
    try {
      await terminateSumupCheckout(input.event.id, readerId)
    } catch {
      /* best effort cleanup */
    }
    throw err
  }
}
