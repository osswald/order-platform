import { describe, expect, it } from 'vitest'
import type { ApplianceRead } from '@/types/api'
import { filterApplianceList } from './applianceListFilters'

const alwaysMatch = () => true
const neverMatch = () => false

function device(
  overrides: Partial<ApplianceRead> & Pick<ApplianceRead, 'id' | 'type'>,
): ApplianceRead {
  return {
    lending_status: 'available',
    lendable: true,
    ...overrides,
  }
}

const sampleDevices: ApplianceRead[] = [
  device({ id: 1, type: 'server', lending_status: 'available' }),
  device({ id: 2, type: 'printer', lending_status: 'lent', ip_address: '192.168.1.10' }),
  device({ id: 3, type: 'printer', lending_status: 'available', ip_address: '192.168.1.20' }),
  device({ id: 4, type: 'mobile', lending_status: 'lent' }),
]

describe('filterApplianceList', () => {
  it('returns all devices when no filters are set', () => {
    const result = filterApplianceList(
      sampleDevices,
      { search: '', type: '', ip: '', lendingStatus: '' },
      alwaysMatch,
    )

    expect(result).toHaveLength(4)
  })

  it('filters by lending status lent', () => {
    const result = filterApplianceList(
      sampleDevices,
      { search: '', type: '', ip: '', lendingStatus: 'lent' },
      alwaysMatch,
    )

    expect(result.map((item) => item.id)).toEqual([2, 4])
  })

  it('filters by lending status available', () => {
    const result = filterApplianceList(
      sampleDevices,
      { search: '', type: '', ip: '', lendingStatus: 'available' },
      alwaysMatch,
    )

    expect(result.map((item) => item.id)).toEqual([1, 3])
  })

  it('combines type, ip, and lending status filters', () => {
    const result = filterApplianceList(
      sampleDevices,
      { search: '', type: 'printer', ip: 'with-ip', lendingStatus: 'available' },
      alwaysMatch,
    )

    expect(result.map((item) => item.id)).toEqual([3])
  })

  it('applies search matching via callback', () => {
    const result = filterApplianceList(
      sampleDevices,
      { search: 'ignored', type: '', ip: '', lendingStatus: '' },
      neverMatch,
    )

    expect(result).toEqual([])
  })
})
