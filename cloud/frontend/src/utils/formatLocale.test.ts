import { describe, expect, it } from 'vitest'
import { resolveFormatLocale } from './formatLocale'

describe('resolveFormatLocale', () => {
  it('maps UI locale and country to BCP 47 tags', () => {
    expect(resolveFormatLocale('de', 'CH')).toBe('de-CH')
    expect(resolveFormatLocale('en', 'CH')).toBe('en-CH')
    expect(resolveFormatLocale('de', 'DE')).toBe('de-DE')
    expect(resolveFormatLocale('en', null)).toBe('en-CH')
  })
})
