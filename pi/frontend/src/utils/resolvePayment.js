import { ref } from 'vue'
import { collectTerminalPayment } from './androidTerminal'
import { pickPaymentType } from './pickPaymentType'
import { buildPayment, buildStripeTerminalPayment } from './paymentTypes'
import {
  checkCloudReachable,
  isStripeTerminalAndroidReady,
  stripeTerminalDisabledHint,
} from './stripeTerminalAvailability'

export const terminalPaymentBusy = ref(false)

export async function resolvePaymentsForAmount(event, amountCents, clientOrderId = null, hooks = {}) {
  const payType = await pickPaymentType(event, amountCents, hooks)
  if (payType !== 'stripe_terminal') {
    return buildPayment(amountCents, payType)
  }

  const androidReady = isStripeTerminalAndroidReady()
  const { reachable: cloudReady } = await checkCloudReachable(true)
  const hint = stripeTerminalDisabledHint(androidReady, cloudReady)
  if (hint) {
    throw new Error(hint)
  }

  terminalPaymentBusy.value = true
  try {
    const payment = await collectTerminalPayment({
      eventId: event.id,
      amountCents,
      currency: event.currency,
      clientOrderId,
    })
    return buildStripeTerminalPayment(amountCents, payment.stripe_payment_intent_id)
  } finally {
    terminalPaymentBusy.value = false
  }
}
