import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../api', () => ({
  apiJson: vi.fn(),
}))

import { apiJson } from '../api'
import { useCountries } from './useCountries'

describe('useCountries', () => {
  beforeEach(() => {
    vi.mocked(apiJson).mockReset()
    const { invalidateCountries } = useCountries()
    invalidateCountries()
  })

  it('fetchCountries loads and maps country options', async () => {
    vi.mocked(apiJson).mockResolvedValue([
      { id: 1, name: 'Schweiz' },
      { id: 2, name: 'Deutschland' },
    ])
    const { fetchCountries, countryOptions, countryName, countryById } = useCountries()

    const rows = await fetchCountries()
    expect(rows).toHaveLength(2)
    expect(countryOptions.value).toEqual([
      { title: 'Schweiz', value: 1 },
      { title: 'Deutschland', value: 2 },
    ])
    expect(countryName(1)).toBe('Schweiz')
    expect(countryById(2)?.name).toBe('Deutschland')
    expect(apiJson).toHaveBeenCalledTimes(1)
  })

  it('fetchCountries returns cached data without refetching', async () => {
    vi.mocked(apiJson).mockResolvedValue([{ id: 1, name: 'Schweiz' }])
    const { fetchCountries } = useCountries()

    await fetchCountries()
    await fetchCountries()
    expect(apiJson).toHaveBeenCalledTimes(1)
  })

  it('fetchCountries dedupes concurrent loads', async () => {
    let resolveFetch!: () => void
    vi.mocked(apiJson).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveFetch = () => resolve([{ id: 1, name: 'Schweiz' }])
        }),
    )
    const { fetchCountries } = useCountries()

    const first = fetchCountries()
    const second = fetchCountries()
    resolveFetch()
    await Promise.all([first, second])
    expect(apiJson).toHaveBeenCalledTimes(1)
  })

  it('invalidateCountries clears cache and allows refetch', async () => {
    vi.mocked(apiJson).mockResolvedValue([{ id: 1, name: 'Schweiz' }])
    const { fetchCountries, invalidateCountries } = useCountries()

    await fetchCountries()
    invalidateCountries()
    await fetchCountries()
    expect(apiJson).toHaveBeenCalledTimes(2)
  })
})
