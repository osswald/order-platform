import { describe, expect, it } from 'vitest'
import {
  COLLECTIVE_RETURN_TO_REGISTER,
  collectiveOpenLocation,
  hubLocationFromCollectiveReturn,
  payCollectiveLocation,
  pickCollectiveReturnQuery,
  registerCollectiveOpenLocation,
} from './collectiveReturnNav'

describe('collectiveReturnNav', () => {
  it('picks register return query only when both keys are valid', () => {
    expect(
      pickCollectiveReturnQuery({
        returnTo: COLLECTIVE_RETURN_TO_REGISTER,
        registerUuid: 'reg-1',
        id: '9',
      }),
    ).toEqual({
      returnTo: COLLECTIVE_RETURN_TO_REGISTER,
      registerUuid: 'reg-1',
    })
    expect(pickCollectiveReturnQuery({ returnTo: COLLECTIVE_RETURN_TO_REGISTER })).toEqual({})
    expect(pickCollectiveReturnQuery({})).toEqual({})
  })

  it('resolves hub back-target from return query', () => {
    expect(
      hubLocationFromCollectiveReturn({
        returnTo: COLLECTIVE_RETURN_TO_REGISTER,
        registerUuid: 'reg-1',
      }),
    ).toEqual({
      name: 'register-hub',
      params: { registerUuid: 'reg-1' },
    })
    expect(hubLocationFromCollectiveReturn({})).toEqual({ name: 'hub' })
  })

  it('builds register entry and preserves return query into pay/list locations', () => {
    expect(registerCollectiveOpenLocation('reg-1')).toEqual({
      name: 'collective-open',
      query: {
        returnTo: COLLECTIVE_RETURN_TO_REGISTER,
        registerUuid: 'reg-1',
      },
    })
    const query = {
      returnTo: COLLECTIVE_RETURN_TO_REGISTER,
      registerUuid: 'reg-1',
    }
    expect(payCollectiveLocation(42, query)).toEqual({
      name: 'pay-collective',
      query: { id: '42', ...query },
    })
    expect(collectiveOpenLocation(query)).toEqual({
      name: 'collective-open',
      query,
    })
    expect(collectiveOpenLocation({})).toEqual({ name: 'collective-open' })
  })
})
