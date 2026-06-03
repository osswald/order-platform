import { ref } from 'vue'
import { api, isAndroidApp } from '../api'
import { isBluetoothPrinterConfigured, printEscposBase64 } from '../utils/androidPrinter'
import { getReceiptPaperWidth } from '../utils/receiptPaperWidth'

export const shiftOpenDialogOpen = ref(false)
export const shiftOpenPending = ref(null)
export const shiftOpenAmountChf = ref('')

export function shiftEnabledForEvent(event) {
  return Boolean(event?.shift_settlement_enabled)
}

function parseChfToCents(input) {
  const normalized = String(input || '').trim().replace(',', '.')
  const value = parseFloat(normalized)
  if (Number.isNaN(value) || value < 0) return null
  return Math.round(value * 100)
}

export function formatCentsChf(cents) {
  return (Number(cents || 0) / 100).toFixed(2)
}

export async function fetchActiveShift({ eventId, subjectType, waiterUuid, cashRegisterUuid }) {
  const params = new URLSearchParams({
    event_id: String(eventId),
    subject_type: subjectType,
  })
  if (waiterUuid) params.set('waiter_uuid', waiterUuid)
  if (cashRegisterUuid) params.set('cash_register_uuid', cashRegisterUuid)
  try {
    return await api(`/v1/shift-session/active?${params}`)
  } catch (e) {
    if (e.status === 404) return null
    throw e
  }
}

export function promptShiftOpen({ eventId, subjectType, waiterUuid, cashRegisterUuid, operatorWaiterUuid }) {
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

export async function confirmShiftOpen() {
  const pending = shiftOpenPending.value
  if (!pending) return
  const cents = parseChfToCents(shiftOpenAmountChf.value)
  if (cents == null) {
    pending.reject(new Error('Ungültiger Betrag'))
    return
  }
  shiftOpenDialogOpen.value = false
  try {
    const session = await api('/v1/shift-session/open', {
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
  } catch (e) {
    pending.reject(e)
  } finally {
    shiftOpenPending.value = null
  }
}

export function cancelShiftOpen() {
  if (shiftOpenPending.value) {
    shiftOpenPending.value.reject(new Error('Abgebrochen'))
  }
  shiftOpenDialogOpen.value = false
  shiftOpenPending.value = null
}

export async function ensureShiftForSubject(ctx) {
  const { event } = ctx
  if (!shiftEnabledForEvent(event)) return null
  const active = await fetchActiveShift(ctx)
  if (active) return active
  return promptShiftOpen(ctx)
}

async function printShiftReceipt(sessionId, countedCents) {
  const body = {
    counted_cash_cents: countedCents,
    paper_width: getReceiptPaperWidth(),
  }
  if (isAndroidApp() && isBluetoothPrinterConfigured()) {
    const data = await api(`/v1/shift-session/${sessionId}/receipt`, {
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

export async function closeShiftFlow(sessionId, countedCents) {
  await api(`/v1/shift-session/${sessionId}/close`, {
    method: 'POST',
    body: JSON.stringify({ counted_cash_cents: countedCents }),
  })
  await printShiftReceipt(sessionId, countedCents)
}

export async function maybeEndShiftOnSwitch(ctx) {
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
