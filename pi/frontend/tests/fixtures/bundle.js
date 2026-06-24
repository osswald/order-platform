/** Test bundle payloads aligned with pi/backend/tests/fixtures_bundles.py */

export function bundleCopy(bundle) {
  return structuredClone(bundle)
}

export function defaultBundle() {
  return {
    organisation_id: 1,
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
          10: { id: 10, name: 'Bier', price: 5.0, additions: [] },
        },
        configuration: { stations: [] },
      },
    ],
  }
}

export function bundleWithAdditions() {
  return {
    organisation_id: 1,
    events: [
      {
        id: 1,
        name: 'Test',
        currency: 'CHF',
        articles: {
          1: {
            id: 1,
            name: 'Article A',
            price: 8.0,
            additions: [{ article_id: 2, name: 'Addon B', price: 3.0 }],
          },
          2: { id: 2, name: 'Addon B', price: 3.0 },
        },
        configuration: { stations: [] },
      },
    ],
  }
}

export function bundleWithWaiters() {
  const b = defaultBundle()
  b.events[0].configuration.event_waiters = [
    { uuid: 'waiter-1', name: 'Anna', pin_hash: 'x' },
  ]
  return b
}

export function bundleWithRegisters() {
  const b = defaultBundle()
  b.events[0].configuration.cash_registers = [
    { uuid: 'register-1', name: 'Kasse 1' },
  ]
  return b
}

export function bundleWithStock() {
  const b = defaultBundle()
  b.events[0].articles[10] = {
    id: 10,
    name: 'Bier',
    price: 5.0,
    additions: [],
    monitor_stock: true,
    in_stock: 3,
  }
  b.events[0].articles[20] = {
    id: 20,
    name: 'Zitrone',
    price: 1.0,
    is_addition: true,
    monitor_stock: true,
    in_stock: 2,
  }
  b.events[0].articles[11] = {
    id: 11,
    name: 'Radler',
    price: 6.0,
    additions: [{ article_id: 20, name: 'Zitrone', price: 1.0 }],
  }
  return b
}

export function discountsBundle() {
  const b = defaultBundle()
  b.events[0].discounts_enabled = true
  b.events[0].articles[11] = { id: 11, name: 'Wein', price: 10.0, additions: [] }
  return b
}

export function positionCommentsBundle() {
  const b = defaultBundle()
  b.position_comments_enabled = true
  b.position_comment_presets = [
    { id: 1, text: 'ohne Zwiebeln' },
    { id: 2, text: 'extra scharf' },
  ]
  return b
}
