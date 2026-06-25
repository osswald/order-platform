import type { ApplianceRead } from '@/types/api'

export type ApplianceListFilters = {
  search: string
  type: string
  ip: '' | 'with-ip' | 'without-ip'
  lendingStatus: '' | 'available' | 'lent'
}

export function filterApplianceList(
  devices: ApplianceRead[],
  filters: ApplianceListFilters,
  matchesSearch: (device: ApplianceRead, term: string) => boolean,
): ApplianceRead[] {
  const term = filters.search.trim().toLowerCase()

  return devices.filter((device) => {
    if (!matchesSearch(device, term)) return false
    if (filters.type && device.type !== filters.type) return false
    const hasIp = !!device.ip_address
    if (filters.ip === 'with-ip' && !hasIp) return false
    if (filters.ip === 'without-ip' && hasIp) return false
    if (filters.lendingStatus && device.lending_status !== filters.lendingStatus) return false
    return true
  })
}
