import type { EdgeBundleResponse } from '@/types/api'

/** Test bundle payloads aligned with pi/backend/tests/fixtures_bundles.py */

export function bundleCopy(bundle: EdgeBundleResponse): EdgeBundleResponse {
  return structuredClone(bundle)
}

export function defaultBundle(): EdgeBundleResponse {
  return {
    organisation_id: 1,
    ingredients_enabled: false,
    position_comments_enabled: false,
    position_comment_presets: [],
    events: [
      {
        id: 1,
        name: 'Test',
        currency: 'CHF',
        payment_mode: 'pay_later',
        payment_types: ['cash'],
        articles: {
          '10': { id: 10, name: 'Bier', price: 5.0, additions: [] },
        },
        configuration: { stations: [] },
      },
    ],
  } as EdgeBundleResponse
}

export function bundleWithAdditions(): EdgeBundleResponse {
  return {
    organisation_id: 1,
    events: [
      {
        id: 1,
        name: 'Test',
        currency: 'CHF',
        payment_mode: 'pay_later',
        articles: {
          '1': {
            id: 1,
            name: 'Article A',
            price: 8.0,
            additions: [{ article_id: 2, name: 'Addon B', price: 3.0 }],
          },
          '2': { id: 2, name: 'Addon B', price: 3.0 },
        },
        configuration: { stations: [] },
      },
    ],
  } as unknown as EdgeBundleResponse
}

export function bundleWithWaiters(): EdgeBundleResponse {
  const b = defaultBundle()
  const ev = b.events![0]
  ev.configuration = {
    ...ev.configuration,
    event_waiters: [{ uuid: 'waiter-1', name: 'Anna', pin_hash: 'x' }],
  }
  return b
}

export function bundleWithRegisters(): EdgeBundleResponse {
  const b = defaultBundle()
  const ev = b.events![0]
  ev.configuration = {
    ...ev.configuration,
    cash_registers: [{ uuid: 'register-1', name: 'Kasse 1' }],
  }
  return b
}

export function bundleWithStock(): EdgeBundleResponse {
  const b = defaultBundle()
  const ev = b.events![0]
  const articles = { ...ev.articles }
  articles['10'] = {
    id: 10,
    name: 'Bier',
    price: 5.0,
    additions: [],
    monitor_stock: true,
    in_stock: 3,
  }
  articles['20'] = {
    id: 20,
    name: 'Zitrone',
    price: 1.0,
    is_addition: true,
    monitor_stock: true,
    in_stock: 2,
  }
  articles['11'] = {
    id: 11,
    name: 'Radler',
    price: 6.0,
    additions: [{ article_id: 20, name: 'Zitrone', price: 1.0 }],
  }
  ev.articles = articles
  return b
}

export function discountsBundle(): EdgeBundleResponse {
  const b = defaultBundle()
  const ev = b.events![0]
  ev.discounts_enabled = true
  ev.articles = {
    ...ev.articles,
    '11': { id: 11, name: 'Wein', price: 10.0, additions: [] },
  }
  return b
}

export function positionCommentsBundle(): EdgeBundleResponse {
  const b = defaultBundle()
  b.position_comments_enabled = true
  b.position_comment_presets = [
    { id: 1, text: 'ohne Zwiebeln' },
    { id: 2, text: 'extra scharf' },
  ]
  return b
}
