import { ref } from 'vue'
import type { EdgeBundleEvent, PaymentIn } from '@/types/api'
import { pickPaymentType, type PickPaymentHooks } from './pickPaymentType'
import { buildPayment } from './paymentTypes'
import { checkCloudReachable } from './cloudReachable'
import { collectSumupConnectedPayment } from './sumupCheckout'

export const terminalPaymentBusy = ref(false)

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
    throw err
  } finally {
    terminalPaymentBusy.value = false
  }
}
