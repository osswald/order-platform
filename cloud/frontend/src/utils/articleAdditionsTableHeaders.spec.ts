import { describe, expect, it } from 'vitest'
import { articleAdditionsTableHeaders } from './articleAdditionsTableHeaders'

describe('articleAdditionsTableHeaders', () => {
  it('places combine-on-kitchen-display next to Vorauswahl Pi', () => {
    const headers = articleAdditionsTableHeaders((key) => key)
    const keys = headers.map((h) => h.key)
    expect(keys).toContain('preselected')
    expect(keys).toContain('combine_on_kitchen_display')
    expect(keys.indexOf('combine_on_kitchen_display')).toBe(keys.indexOf('preselected') + 1)
  })
})
