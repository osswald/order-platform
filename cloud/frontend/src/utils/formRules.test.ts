import { describe, expect, it } from 'vitest'
import { rules } from './formRules'

describe('rules.required', () => {
  it('rejects empty values', () => {
    expect(rules.required('')).toBe('Pflichtfeld')
    expect(rules.required(null)).toBe('Pflichtfeld')
    expect(rules.required('  ')).toBe('Pflichtfeld')
    expect(rules.required('ok')).toBe(true)
  })
})

describe('rules.requiredArray', () => {
  it('requires a non-empty array', () => {
    expect(rules.requiredArray([])).toBe('Pflichtfeld')
    expect(rules.requiredArray([1])).toBe(true)
  })
})

describe('rules.requiredDate', () => {
  it('requires a valid Date instance', () => {
    expect(rules.requiredDate(null)).toBe('Pflichtfeld')
    expect(rules.requiredDate(new Date('invalid'))).toBe('Pflichtfeld')
    expect(rules.requiredDate(new Date('2026-01-01'))).toBe(true)
  })
})

describe('rules.requiredNumber', () => {
  it('requires a numeric value', () => {
    expect(rules.requiredNumber('')).toBe('Pflichtfeld')
    expect(rules.requiredNumber('abc')).toBe('Pflichtfeld')
    expect(rules.requiredNumber('12')).toBe(true)
  })
})

describe('rules.minNumber', () => {
  it('enforces a minimum numeric value', () => {
    const min5 = rules.minNumber(5)
    expect(min5(4)).toBe('Pflichtfeld')
    expect(min5(5)).toBe(true)
  })
})

describe('rules.email', () => {
  it('validates email format', () => {
    expect(rules.email('')).toBe('Pflichtfeld')
    expect(rules.email('not-an-email')).toBe('Ungültige E-Mail-Adresse')
    expect(rules.email('admin@example.com')).toBe(true)
  })
})

describe('rules.passwordMatch', () => {
  it('compares against the other password', () => {
    const matcher = rules.passwordMatch('secret')
    expect(matcher('wrong')).toBe('Passwörter stimmen nicht überein')
    expect(matcher('secret')).toBe(true)
  })
})
