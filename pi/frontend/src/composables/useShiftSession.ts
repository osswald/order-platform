import { ref } from 'vue'
import { api, isAndroidApp } from '@/api'
import type { EdgeBundleEvent, ShiftSessionRead } from '@/types/api'
import { isApiError } from '@/types/api'
import { isBluetoothPrinterConfigured, printEscposBase64 } from '@/utils/androidPrinter'
import { getReceiptPaperWidth } from '@/utils/receiptPaperWidth'

export const shiftOpenDialogOpen = ref(false)

interface ShiftOpenPending {
  eventId: number
  subjectType: 'waiter' | 'cash_register'
  waiterUuid?: string | null
  cashRegisterUuid?: string | null
  operatorWaiterUuid?: string | null
  resolve: (value: ShiftSessionRead) => void
  reject: (reason?: unknown) => void
}

export const shiftOpenPending = ref<ShiftOpenPending | null>(null)
export const shiftOpenAmountChf = ref('')

export function shiftEnabledForEvent(event: EdgeBundleEvent | null | undefined): boolean {
  return Boolean(event?.shift_settlement_enabled)
}

function parseChfToCents(input: string | null | undefined): number | null {
  const normalized = String(input || '').trim().replace(',', '.')
  const value = parseFloat(normalized)
  if (Number.isNaN(value) || value < 0) return null
  return Math.round(value * 100)
}

export function formatCentsChf(cents: number | null | undefined): string {
  return (Number(cents || 0) / 100).toFixed(2)
}

export interface FetchActiveShiftInput {
  eventId: number
  subjectType: 'waiter' | 'cash_register'
  waiterUuid?: string | null
  cashRegisterUuid?: string | null
}

export async function fetchActiveShift({
  eventId,
  subjectType,
  waiterUuid,
  cashRegisterUuid,
}: FetchActiveShiftInput): Promise<ShiftSessionRead | null> {
  const params = new URLSearchParams({
    event_id: String(eventId),
    subject_type: subjectType,
  })
  if (waiterUuid) params.set('waiter_uuid', waiterUuid)
  if (cashRegisterUuid) params.set('cash_register_uuid', cashRegisterUuid)
  try {
    return await api<ShiftSessionRead>(`/v1/shift-session/active?${params}`)
  } catch (e: unknown) {
    if (isApiError(e) && e.status === 404) return null
    throw e
  }
}

export interface PromptShiftOpenInput extends FetchActiveShiftInput {
  operatorWaiterUuid?: string | null
}

export function promptShiftOpen({
  eventId,
  subjectType,
  waiterUuid,
  cashRegisterUuid,
  operatorWaiterUuid,
}: PromptShiftOpenInput): Promise<ShiftSessionRead> {
  return new Promise((resolve, reject) => {
    shiftOpenPending.value = {
      eventId,
      subjectType,
      waiterUuid,
      cashRegisterUuid,
      operatorWaiterUuid,
      resolve,
      reject,
    }
    shiftOpenAmountChf.value = '0.00'
    shiftOpenDialogOpen.value = true
  })
}

export async function confirmShiftOpen(): Promise<void> {
  const pending = shiftOpenPending.value
  if (!pending) return
  const cents = parseChfToCents(shiftOpenAmountChf.value)
  if (cents == null) {
    pending.reject(new Error('Ungültiger Betrag'))
    return
  }
  shiftOpenDialogOpen.value = false
  try {
    const session = await api<ShiftSessionRead>('/v1/shift-session/open', {
      method: 'POST',
      body: JSON.stringify({
        event_id: pending.eventId,
        subject_type: pending.subjectType,
        waiter_uuid: pending.waiterUuid,
        cash_register_uuid: pending.cashRegisterUuid,
        operator_waiter_uuid: pending.operatorWaiterUuid,
        opening_balance_cents: cents,
      }),
    })
    pending.resolve(session)
  } catch (e: unknown) {
    pending.reject(e)
  } finally {
    shiftOpenPending.value = null
  }
}

export function cancelShiftOpen(): void {
  if (shiftOpenPending.value) {
    shiftOpenPending.value.reject(new Error('Abgebrochen'))
  }
  shiftOpenDialogOpen.value = false
  shiftOpenPending.value = null
}

export interface ShiftSubjectContext extends FetchActiveShiftInput {
  event: EdgeBundleEvent
}

export async function ensureShiftForSubject(ctx: ShiftSubjectContext): Promise<ShiftSessionRead | null> {
  const { event } = ctx
  if (!shiftEnabledForEvent(event)) return null
  const active = await fetchActiveShift(ctx)
  if (active) return active
  return promptShiftOpen(ctx)
}

async function printShiftReceipt(sessionId: number, countedCents: number): Promise<void> {
  const body = {
    counted_cash_cents: countedCents,
    paper_width: getReceiptPaperWidth(),
  }
  if (isAndroidApp() && isBluetoothPrinterConfigured()) {
    const data = await api<{ escpos_payload: string }>(`/v1/shift-session/${sessionId}/receipt`, {
      method: 'POST',
      body: JSON.stringify(body),
    })
    const result = printEscposBase64(data.escpos_payload)
    if (!result.ok) {
      throw new Error(result.error || 'Schichtabrechnung konnte nicht gedruckt werden.')
    }
    return
  }
  await api(`/v1/shift-session/${sessionId}/print`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function closeShiftFlow(sessionId: number, countedCents: number): Promise<void> {
  await api(`/v1/shift-session/${sessionId}/close`, {
    method: 'POST',
    body: JSON.stringify({ counted_cash_cents: countedCents }),
  })
  await printShiftReceipt(sessionId, countedCents)
}

export async function maybeEndShiftOnSwitch(ctx: ShiftSubjectContext): Promise<boolean> {
  const { event } = ctx
  if (!shiftEnabledForEvent(event)) return true
  const active = await fetchActiveShift(ctx)
  if (!active) return true
  const end = window.confirm('Schicht beenden?')
  if (!end) {
    window.alert('Schicht bleibt offen. Bitte später abschliessen.')
    return true
  }
  const countedStr = window.prompt(
    `Kassenbestand zählen (CHF).\nErwartet ca. ${formatCentsChf(active.wallet_cents)}:`,
    formatCentsChf(active.wallet_cents),
  )
  if (countedStr == null) return false
  const cents = parseChfToCents(countedStr)
  if (cents == null) {
    window.alert('Ungültiger Betrag')
    return false
  }
  await closeShiftFlow(active.id, cents)
  return true
}
