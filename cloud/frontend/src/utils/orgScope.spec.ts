import { describe, expect, it } from 'vitest'
import { organisationAccountsEnabled, organisationIngredientsEnabled } from './orgScope'

describe('organisationAccountsEnabled', () => {
  const organisations = [
    { id: 1, name: 'Org A', accounts_enabled: true },
    { id: 2, name: 'Org B', accounts_enabled: false },
    { id: 3, name: 'Org C', accounts_enabled: false },
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

describe('organisationIngredientsEnabled', () => {
  const organisations = [
    { id: 1, name: 'Org A', ingredients_enabled: true },
    { id: 2, name: 'Org B', ingredients_enabled: false },
    { id: 3, name: 'Org C', ingredients_enabled: false },
  ]

  it('returns true when the active org has ingredients_enabled', () => {
    expect(organisationIngredientsEnabled(organisations, 1)).toBe(true)
  })

  it('returns false when ingredients_enabled is false', () => {
    expect(organisationIngredientsEnabled(organisations, 2)).toBe(false)
  })

  it('returns false when ingredients_enabled is missing', () => {
    expect(organisationIngredientsEnabled(organisations, 3)).toBe(false)
  })

  it('returns false when organisation id is null or org list is empty', () => {
    expect(organisationIngredientsEnabled(organisations, null)).toBe(false)
    expect(organisationIngredientsEnabled([], 1)).toBe(false)
  })
})
