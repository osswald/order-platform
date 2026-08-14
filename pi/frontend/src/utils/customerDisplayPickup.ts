/** Customer display success / pickup helpers (pure). */

import type { EdgeBundleEvent } from '@/types/api'
import { stationNameFromEvent } from './bundleHelpers'

export type DisplayPickupIn = {
  pickup_code?: string | null
  station_uuid?: string | null
  station_name?: string | null
}

export type DisplayPickupOut = {
  pickup_code: string
  station_uuid: string | null
  station_name: string
}

export type DisplayPickupBadge = {
  code: string
  stationName: string
}

export function pickupCodesForDisplay(payload: {
  pickup_codes?: string[] | null
  pickup_code?: string | null
}): string[] {
  const codes = (payload.pickup_codes || []).map(String).filter(Boolean)
  if (codes.length) return codes
  const single = payload.pickup_code != null ? String(payload.pickup_code).trim() : ''
  return single ? [single] : []
}

export function displayPickupsFromSummary(
  pickups: DisplayPickupIn[] | null | undefined,
  event: EdgeBundleEvent | null | undefined,
): DisplayPickupOut[] {
  return (pickups || [])
    .map((p) => {
      const pickup_code = String(p.pickup_code || '').trim()
      const rawUuid = p.station_uuid != null ? String(p.station_uuid).trim() : ''
      const station_uuid = rawUuid || null
      const station_name = String(p.station_name || '').trim() || stationNameFromEvent(event, station_uuid)
      return { pickup_code, station_uuid, station_name }
    })
    .filter((p) => p.pickup_code)
}

export function pickupBadgesForDisplay(
  payload: {
    pickups?: DisplayPickupIn[] | null
    pickup_codes?: string[] | null
    pickup_code?: string | null
  },
  event?: EdgeBundleEvent | null,
): DisplayPickupBadge[] {
  const fromPickups = displayPickupsFromSummary(payload.pickups, event).map((p) => ({
    code: p.pickup_code,
    stationName: p.station_name,
  }))
  if (fromPickups.length) return fromPickups
  return pickupCodesForDisplay(payload).map((code) => ({ code, stationName: '' }))
}

export function abholbonFooterText(codeCount: number): string {
  if (codeCount >= 2) return 'Bitte Abholbons mitnehmen'
  return 'Bitte Abholbon mitnehmen'
}
