import type { EdgeBundleEvent, EdgeBundleResponse } from '@/types/api'
import { eventPaymentTypes } from './paymentTypes'

export interface SumupBundleReader {
  sumup_reader_id: string
  label: string
}

type BundleWithReaders = EdgeBundleResponse & {
  sumup_readers?: SumupBundleReader[] | null
}

export function getBundleSumupReaders(bundle: EdgeBundleResponse | null | undefined): SumupBundleReader[] {
  const raw = (bundle as BundleWithReaders | null | undefined)?.sumup_readers
  if (!Array.isArray(raw)) return []
  const out: SumupBundleReader[] = []
  for (const item of raw) {
    if (!item || typeof item !== 'object') continue
    const readerId = String((item as SumupBundleReader).sumup_reader_id || '').trim()
    const label = String((item as SumupBundleReader).label || '').trim()
    if (!readerId || !label) continue
    out.push({ sumup_reader_id: readerId, label })
  }
  return out
}

export function eventNeedsSumupReaderPicker(
  event: EdgeBundleEvent | null | undefined,
  readers: SumupBundleReader[],
): boolean {
  if (!event || readers.length === 0) return false
  return eventPaymentTypes(event).includes('sumup_connected') && readers.length > 1
}

export function autoSelectSumupReader(readers: SumupBundleReader[]): SumupBundleReader | null {
  if (readers.length !== 1) return null
  return readers[0]
}

export function findSumupReaderLabel(readers: SumupBundleReader[], readerId: string): string | null {
  const match = readers.find((r) => r.sumup_reader_id === readerId)
  return match?.label ?? null
}

export function resolveRegisterSumupReaderId(
  event: EdgeBundleEvent | null | undefined,
  registerUuid: string | null | undefined,
): string | null {
  if (!event || !registerUuid) return null
  const reg = (event.configuration?.cash_registers || []).find(
    (x) => String(x.uuid) === String(registerUuid),
  )
  const readerId = reg && 'sumup_reader_id' in reg ? String(reg.sumup_reader_id || '').trim() : ''
  return readerId || null
}
