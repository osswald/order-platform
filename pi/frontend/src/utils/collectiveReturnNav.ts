import type { LocationQuery, RouteLocationRaw } from 'vue-router'

/** Query value for `returnTo` when entered from the cash register hub. */
export const COLLECTIVE_RETURN_TO_REGISTER = 'register-hub'

/** Keep only register-return query keys needed for hub back-navigation. */
export function pickCollectiveReturnQuery(query: LocationQuery): Record<string, string> {
  const returnTo = typeof query.returnTo === 'string' ? query.returnTo : ''
  const registerUuid = typeof query.registerUuid === 'string' ? query.registerUuid : ''
  if (returnTo === COLLECTIVE_RETURN_TO_REGISTER && registerUuid) {
    return { returnTo, registerUuid }
  }
  return {}
}

/** Waiter hub, or register hub when return query is present. */
export function hubLocationFromCollectiveReturn(query: LocationQuery): RouteLocationRaw {
  const picked = pickCollectiveReturnQuery(query)
  if (picked.returnTo === COLLECTIVE_RETURN_TO_REGISTER && picked.registerUuid) {
    return {
      name: 'register-hub',
      params: { registerUuid: picked.registerUuid },
    }
  }
  return { name: 'hub' }
}

/** Entry location from RegisterHubView into the collective list. */
export function registerCollectiveOpenLocation(registerUuid: string): RouteLocationRaw {
  return {
    name: 'collective-open',
    query: {
      returnTo: COLLECTIVE_RETURN_TO_REGISTER,
      registerUuid,
    },
  }
}

/** Open a bill while preserving register return context. */
export function payCollectiveLocation(
  billId: number | string,
  query: LocationQuery,
): RouteLocationRaw {
  return {
    name: 'pay-collective',
    query: {
      id: String(billId),
      ...pickCollectiveReturnQuery(query),
    },
  }
}

/** Return to the collective list while preserving register return context. */
export function collectiveOpenLocation(query: LocationQuery): RouteLocationRaw {
  const picked = pickCollectiveReturnQuery(query)
  return Object.keys(picked).length
    ? { name: 'collective-open', query: picked }
    : { name: 'collective-open' }
}
