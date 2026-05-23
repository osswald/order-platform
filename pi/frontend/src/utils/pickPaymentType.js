import { ref } from 'vue'
import { formatAmount } from './money'
import { eventPaymentTypes, eventTwintQrDataUrl } from './paymentTypes'

export const pickerOpen = ref(false)
export const pickerTypes = ref([])
export const pickerAmountLabel = ref('')

export const twintQrOpen = ref(false)
export const twintQrDataUrl = ref('')
export const twintQrAmountLabel = ref('')

let resolvePick = null
let rejectPick = null
let resolveTwintQr = null
let rejectTwintQr = null

function amountLabelFor(cents) {
  if (cents != null) return formatAmount(cents)
  return ''
}

function pickTypeFromSheet(event, amountCents) {
  const types = eventPaymentTypes(event)
  if (types.length === 1) {
    return Promise.resolve(types[0])
  }
  pickerTypes.value = types
  pickerAmountLabel.value = amountLabelFor(amountCents)
  pickerOpen.value = true
  return new Promise((resolve, reject) => {
    resolvePick = resolve
    rejectPick = reject
  })
}

export function showTwintQr(dataUrl, amountLabel = '') {
  twintQrDataUrl.value = dataUrl
  twintQrAmountLabel.value = amountLabel
  twintQrOpen.value = true
  return new Promise((resolve, reject) => {
    resolveTwintQr = resolve
    rejectTwintQr = reject
  })
}

export async function pickPaymentType(event, amountCents = null) {
  const type = await pickTypeFromSheet(event, amountCents)
  const qrUrl = type === 'twint' ? eventTwintQrDataUrl(event) : null
  if (qrUrl) {
    const label = pickerAmountLabel.value || amountLabelFor(amountCents)
    await showTwintQr(qrUrl, label)
  }
  return type
}

export function confirmPaymentType(type) {
  pickerOpen.value = false
  const r = resolvePick
  resolvePick = null
  rejectPick = null
  if (r) r(type)
}

export function cancelPaymentType() {
  pickerOpen.value = false
  const rej = rejectPick
  resolvePick = null
  rejectPick = null
  if (rej) rej(new Error('cancelled'))
}

export function confirmTwintQr() {
  twintQrOpen.value = false
  const r = resolveTwintQr
  resolveTwintQr = null
  rejectTwintQr = null
  if (r) r()
}

export function cancelTwintQr() {
  twintQrOpen.value = false
  const rej = rejectTwintQr
  resolveTwintQr = null
  rejectTwintQr = null
  if (rej) rej(new Error('cancelled'))
}
