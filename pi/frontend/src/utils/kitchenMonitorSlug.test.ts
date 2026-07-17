import { describe, expect, it } from 'vitest'
import {
  assignKitchenMonitorSlugs,
  kitchenMonitorPrinterBySlug,
  slugifyKitchenMonitorLabel,
} from './kitchenMonitorSlug'

describe('slugifyKitchenMonitorLabel', () => {
  it('normalizes labels to url-safe slugs', () => {
    expect(slugifyKitchenMonitorLabel('Grill')).toBe('grill')
    expect(slugifyKitchenMonitorLabel('Getränke West')).toBe('getraenke-west')
  })
})

describe('assignKitchenMonitorSlugs', () => {
  it('assigns unique slugs and suffixes duplicates', () => {
    const slugs = assignKitchenMonitorSlugs([
      { printer_appliance_id: 101, label: 'Grill' },
      { printer_appliance_id: 102, label: 'Grill' },
      { printer_appliance_id: 103, label: 'Bar' },
    ])
    expect(slugs.get(101)).toBe('grill')
    expect(slugs.get(102)).toBe('grill-102')
    expect(slugs.get(103)).toBe('bar')
  })
})

describe('kitchenMonitorPrinterBySlug', () => {
  it('resolves printer by slug', () => {
    const printers = [
      { printer_appliance_id: 101, label: 'Grill', sort_order: 0 },
      { printer_appliance_id: 102, label: 'Getränke Ost', sort_order: 1 },
    ]
    expect(kitchenMonitorPrinterBySlug('grill', printers)?.printer_appliance_id).toBe(101)
    expect(kitchenMonitorPrinterBySlug('getraenke-ost', printers)?.printer_appliance_id).toBe(102)
    expect(kitchenMonitorPrinterBySlug('missing', printers)).toBeNull()
  })
})
