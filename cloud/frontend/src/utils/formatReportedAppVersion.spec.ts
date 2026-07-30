import { describe, expect, it } from 'vitest'
import { formatReportedAppVersion } from './formatReportedAppVersion'

describe('formatReportedAppVersion', () => {
  it('formats version with build time like Pi Admin', () => {
    expect(formatReportedAppVersion('1.5.10', '202607201045')).toBe('v1.5.10 (202607201045)')
  })

  it('formats version alone when build time missing or dev', () => {
    expect(formatReportedAppVersion('1.5.10')).toBe('v1.5.10')
    expect(formatReportedAppVersion('1.5.10', null)).toBe('v1.5.10')
    expect(formatReportedAppVersion('1.5.10', 'dev')).toBe('v1.5.10')
  })

  it('returns empty label when never reported', () => {
    expect(formatReportedAppVersion(null)).toBe('—')
    expect(formatReportedAppVersion(undefined)).toBe('—')
    expect(formatReportedAppVersion('')).toBe('—')
    expect(formatReportedAppVersion('   ', null, '—')).toBe('—')
  })
})
