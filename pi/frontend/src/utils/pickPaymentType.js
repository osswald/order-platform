import { ref } from 'vue'
import { formatAmount } from './money'
import { eventPaymentTypes, eventTwintQrDataUrl } from './paymentTypes'
import { stripeTerminalPickerEntry } from './stripeTerminalAvailability'

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

function entryValue(entry) {
  return typeof entry === 'object' && entry != null ? entry.value : entry
}

function entryDisabled(entry) {
  return Boolean(typeof entry === 'object' && entry != null && entry.disabled)
}

async function buildPickerEntries(event) {
  const types = eventPaymentTypes(event)
  const entries = []
  for (const t of types) {
    if (t === 'stripe_terminal') {
      entries.push(await stripeTerminalPickerEntry())
    } else {
      entries.push({ value: t, disabled: false })
    }
  }
  return entries
}

async function pickTypeFromSheet(event, amountCents) {
  const entries = await buildPickerEntries(event)
  const enabled = entries.filter((e) => !entryDisabled(e))
  if (entries.length === 1 && enabled.length === 1) {
    return entryValue(enabled[0])
  }
  pickerTypes.value = entries
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

export async function pickPaymentType(event, amountCents = null, hooks = {}) {
  const type = await pickTypeFromSheet(event, amountCents)
  const qrUrl = type === 'twint' ? eventTwintQrDataUrl(event) : null
  if (qrUrl) {
    const label = pickerAmountLabel.value || amountLabelFor(amountCents)
    hooks.onTwintShow?.({ dataUrl: qrUrl, amountLabel: label, amountCents })
    try {
      await showTwintQr(qrUrl, label)
    } finally {
      hooks.onTwintHide?.()
    }
  }
  return type
}

export function confirmPaymentType(typeOrEntry) {
  const entry =
    typeof typeOrEntry === 'object' && typeOrEntry != null
      ? typeOrEntry
      : pickerTypes.value.find((e) => entryValue(e) === typeOrEntry)
  if (entry && entryDisabled(entry)) {
    return
  }
  const type = entryValue(entry ?? typeOrEntry)
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
