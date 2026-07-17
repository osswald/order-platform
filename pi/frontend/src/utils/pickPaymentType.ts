import { ref } from 'vue'
import type { EdgeBundleEvent } from '@/types/api'
import { formatMoney } from './money'
import { eventPaymentTypes, eventTwintQrDataUrl, type PaymentType } from './paymentTypes'
import { stripeTerminalPickerEntry } from './stripeTerminalAvailability'

export interface PaymentPickerEntry {
  value: PaymentType
  disabled?: boolean
  hint?: string
}

export const pickerOpen = ref(false)
export const pickerTypes = ref<PaymentPickerEntry[]>([])
export const pickerAmountLabel = ref('')

export const twintQrOpen = ref(false)
export const twintQrDataUrl = ref('')
export const twintQrAmountLabel = ref('')

let resolvePick: ((value: PaymentType) => void) | null = null
let rejectPick: ((reason?: unknown) => void) | null = null
let resolveTwintQr: (() => void) | null = null
let rejectTwintQr: ((reason?: unknown) => void) | null = null

function amountLabelFor(cents: number | null | undefined, currency: string): string {
  if (cents != null) return formatMoney(cents, currency)
  return ''
}

function entryValue(entry: PaymentPickerEntry | PaymentType): PaymentType {
  return typeof entry === 'object' && entry != null ? entry.value : entry
}

function entryDisabled(entry: PaymentPickerEntry | PaymentType): boolean {
  return Boolean(typeof entry === 'object' && entry != null && entry.disabled)
}

async function buildPickerEntries(event: EdgeBundleEvent): Promise<PaymentPickerEntry[]> {
  const types = eventPaymentTypes(event)
  const entries: PaymentPickerEntry[] = []
  for (const t of types) {
    if (t === 'stripe_terminal') {
      entries.push(await stripeTerminalPickerEntry())
    } else {
      entries.push({ value: t, disabled: false })
    }
  }
  return entries
}

async function pickTypeFromSheet(event: EdgeBundleEvent, amountCents: number | null): Promise<PaymentType> {
  const entries = await buildPickerEntries(event)
  const enabled = entries.filter((e) => !entryDisabled(e))
  if (entries.length === 1 && enabled.length === 1) {
    return entryValue(enabled[0])
  }
  pickerTypes.value = entries
  pickerAmountLabel.value = amountLabelFor(amountCents, event.currency || 'CHF')
  pickerOpen.value = true
  return new Promise((resolve, reject) => {
    resolvePick = resolve
    rejectPick = reject
  })
}

export function showTwintQr(dataUrl: string, amountLabel = ''): Promise<void> {
  twintQrDataUrl.value = dataUrl
  twintQrAmountLabel.value = amountLabel
  twintQrOpen.value = true
  return new Promise((resolve, reject) => {
    resolveTwintQr = resolve
    rejectTwintQr = reject
  })
}

export interface PickPaymentHooks {
  onTwintShow?: (payload: { dataUrl: string; amountLabel: string; amountCents: number | null }) => void
  onTwintHide?: () => void
}

export async function pickPaymentType(
  event: EdgeBundleEvent,
  amountCents: number | null = null,
  hooks: PickPaymentHooks = {},
): Promise<PaymentType> {
  const type = await pickTypeFromSheet(event, amountCents)
  const qrUrl = type === 'twint' ? eventTwintQrDataUrl(event) : null
  if (qrUrl) {
    const label = pickerAmountLabel.value || amountLabelFor(amountCents, event.currency || 'CHF')
    hooks.onTwintShow?.({ dataUrl: qrUrl, amountLabel: label, amountCents })
    try {
      await showTwintQr(qrUrl, label)
    } finally {
      hooks.onTwintHide?.()
    }
  }
  return type
}

export function confirmPaymentType(typeOrEntry: PaymentPickerEntry | PaymentType): void {
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

export function cancelPaymentType(): void {
  pickerOpen.value = false
  const rej = rejectPick
  resolvePick = null
  rejectPick = null
  if (rej) rej(new Error('cancelled'))
}

export function confirmTwintQr(): void {
  twintQrOpen.value = false
  const r = resolveTwintQr
  resolveTwintQr = null
  rejectTwintQr = null
  if (r) r()
}

export function cancelTwintQr(): void {
  twintQrOpen.value = false
  const rej = rejectTwintQr
  resolveTwintQr = null
  rejectTwintQr = null
  if (rej) rej(new Error('cancelled'))
}
