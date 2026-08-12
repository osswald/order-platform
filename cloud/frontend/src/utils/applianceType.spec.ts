import { describe, expect, it } from 'vitest'
import {
  APPLIANCE_TYPES,
  applianceTypeColor,
  applianceTypeIcon,
  applianceTypeLabel,
  compareApplianceTypes,
} from './applianceType'

describe('applianceType', () => {
  it('lists all six backend-allowed types in display order', () => {
    expect(APPLIANCE_TYPES).toEqual(['server', 'router', 'ap', 'printer', 'mobile', 'tablet'])
    expect(APPLIANCE_TYPES).toHaveLength(6)
  })

  it.each([
    ['server', 'mdi-server', 'primary'],
    ['printer', 'mdi-printer', 'warning'],
    ['mobile', 'mdi-cellphone', 'info'],
    ['tablet', 'mdi-tablet', 'teal'],
    ['router', 'mdi-router-wireless', 'deep-purple'],
    ['ap', 'mdi-wifi', 'success'],
  ])('maps %s to icon %s and color %s', (type, icon, color) => {
    expect(applianceTypeIcon(type)).toBe(icon)
    expect(applianceTypeColor(type)).toBe(color)
  })

  it('falls back for unknown types', () => {
    expect(applianceTypeIcon('unknown')).toBe('mdi-devices')
    expect(applianceTypeColor('unknown')).toBe('default')
    expect(applianceTypeLabel('unknown')).toBe('unknown')
  })

  it('compares types in server → router → ap → printer → mobile → tablet order', () => {
    expect(compareApplianceTypes('server', 'router')).toBeLessThan(0)
    expect(compareApplianceTypes('ap', 'printer')).toBeLessThan(0)
    expect(compareApplianceTypes('printer', 'mobile')).toBeLessThan(0)
    expect(compareApplianceTypes('tablet', 'server')).toBeGreaterThan(0)
    expect(compareApplianceTypes('other', 'server')).toBeGreaterThan(0)
  })
})
