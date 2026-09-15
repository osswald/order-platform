import { ref } from 'vue'
import type { EdgeBundleEvent, PaymentIn } from '@/types/api'
import { pickPaymentType, type PickPaymentHooks } from './pickPaymentType'
import { buildPayment } from './paymentTypes'
import { checkCloudReachable } from './cloudReachable'
import {
  cancelActiveSumupCheckout,
  collectSumupConnectedPayment,
  SUMUP_CANCELLED_MESSAGE,
} from './sumupCheckout'

export const terminalPaymentBusy = ref(false)

/** Operator-visible failure message after a SumUp connected attempt fails (not cancel). */
export const sumupPaymentFailureMessage = ref<string | null>(null)

export function dismissSumupPaymentFailure(): void {
  sumupPaymentFailureMessage.value = null
}

export function cancelActiveSumupPayment(): void {
  cancelActiveSumupCheckout()
}

export async function resolvePaymentsForAmount(
  event: EdgeBundleEvent,
  amountCents: number,
  clientOrderId: string | null = null,
  hooks: PickPaymentHooks = {},
): Promise<PaymentIn[]> {
  const payType = await pickPaymentType(event, amountCents, hooks)
  if (payType !== 'sumup_connected') {
    return buildPayment(amountCents, payType)
  }

  const { reachable: cloudReady } = await checkCloudReachable(true)
  if (!cloudReady) {
    throw new Error('Cloud-Verbindung erforderlich.')
  }

  terminalPaymentBusy.value = true
  hooks.onSumupShow?.({ amountCents })
  try {
    const payment = await collectSumupConnectedPayment({
      event,
      amountCents,
      clientOrderId,
    })
    return [payment]
  } catch (err) {
    hooks.onSumupHide?.()
    const message = err instanceof Error ? err.message : String(err)
    if (message !== SUMUP_CANCELLED_MESSAGE) {
      sumupPaymentFailureMessage.value = message || 'SumUp-Zahlung fehlgeschlagen.'
    }
    throw err
  } finally {
    terminalPaymentBusy.value = false
  }
}
