import { describe, expect, it } from 'vitest'
import { organisationAccountsEnabled } from './orgScope'

describe('organisationAccountsEnabled', () => {
  const organisations = [
    { id: 1, name: 'Org A', accounts_enabled: true },
    { id: 2, name: 'Org B', accounts_enabled: false },
    { id: 3, name: 'Org C' },
  ]

  it('returns true when the active org has accounts_enabled', () => {
    expect(organisationAccountsEnabled(organisations, 1)).toBe(true)
  })

  it('returns false when accounts_enabled is false', () => {
    expect(organisationAccountsEnabled(organisations, 2)).toBe(false)
  })

  it('returns false when accounts_enabled is missing', () => {
    expect(organisationAccountsEnabled(organisations, 3)).toBe(false)
  })

  it('returns false when organisation id is null or org list is empty', () => {
    expect(organisationAccountsEnabled(organisations, null)).toBe(false)
    expect(organisationAccountsEnabled([], 1)).toBe(false)
  })
})
