import { apiFetch } from '../api'
import { parseApiErrorDetail } from './apiError'

export function toIsoDate(d) {
  if (!d) return null
  const x = d instanceof Date ? d : new Date(d)
  const y = x.getFullYear()
  const mo = String(x.getMonth() + 1).padStart(2, '0')
  const day = String(x.getDate()).padStart(2, '0')
  return `${y}-${mo}-${day}`
}

export const APPLIANCE_TYPE_LABELS = {
  server: 'Server',
  printer: 'Drucker',
  mobile: 'Mobil',
  tablet: 'Tablet',
  router: 'Router',
  ap: 'Access Point',
}

export function applianceTypeLabel(type) {
  return APPLIANCE_TYPE_LABELS[type] || type
}

export function applianceDisplayName(appliance) {
  if (appliance?.name) return appliance.name
  return `#${appliance?.id ?? '?'}`
}

export async function cancelPlannedLending(organisationId, lendingId) {
  const response = await apiFetch(
    `/organisations/${organisationId}/appliance-lendings/${lendingId}`,
    { method: 'DELETE' },
  )
  if (!response.ok) {
    throw new Error(await parseApiErrorDetail(response))
  }
}

export async function cancelPlannedLendingForAppliance(applianceId, lendingId) {
  const response = await apiFetch(`/appliances/${applianceId}/lendings/${lendingId}`, {
    method: 'DELETE',
  })
  if (!response.ok) {
    throw new Error(await parseApiErrorDetail(response))
  }
}
