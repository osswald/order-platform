import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../api', () => ({
  apiJson: vi.fn(),
}))

vi.mock('../i18n', () => ({
  i18n: {
    global: {
      t: (key: string) => key,
    },
  },
}))

import { apiJson } from '../api'
import { createApiError } from '../api/auth'
import {
  createStripeAccountLink,
  fetchStripeConnectStatus,
  refreshStripeConnectStatus,
} from './stripeConnect'

describe('stripeConnect', () => {
  beforeEach(() => {
    vi.mocked(apiJson).mockReset()
  })

  it('maps 503 status to configured:false', async () => {
    vi.mocked(apiJson).mockRejectedValue(createApiError('unavailable', 503))
    await expect(fetchStripeConnectStatus(1)).resolves.toEqual({
      configured: false,
      error: 'stripe.notConfigured',
    })
  })

  it('rethrows createStripeAccountLink 503 with cause', async () => {
    const apiErr = createApiError('unavailable', 503)
    vi.mocked(apiJson).mockRejectedValue(apiErr)
    await expect(createStripeAccountLink(1)).rejects.toMatchObject({
      message: 'stripe.notConfigured',
      cause: apiErr,
    })
  })

  it('rethrows refreshStripeConnectStatus 503 with cause', async () => {
    const apiErr = createApiError('unavailable', 503)
    vi.mocked(apiJson).mockRejectedValue(apiErr)
    await expect(refreshStripeConnectStatus(1)).rejects.toMatchObject({
      message: 'stripe.notConfigured',
      cause: apiErr,
    })
  })
})
