import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import { i18n } from '../i18n'

vi.mock('../api', () => ({
  apiJson: vi.fn(),
}))

import { apiJson } from '../api'
import { useHostedPi } from './useHostedPi'

const runningInstance = {
  id: 1,
  event_id: 42,
  status: 'running',
  url: 'https://abc.demo.vendiqo.ch',
  expires_at: '2026-06-25T12:00:00Z',
}

describe('useHostedPi', () => {
  beforeEach(() => {
    vi.mocked(apiJson).mockReset()
  })

  it('loads a running instance on initial fetch', async () => {
    vi.mocked(apiJson).mockResolvedValue(runningInstance)

    const eventId = ref(42)
    const { instance, error, load } = useHostedPi(eventId)

    await load()

    expect(apiJson).toHaveBeenCalledWith('/events/42/hosted-pi')
    expect(instance.value?.status).toBe('running')
    expect(error.value).toBe('')
  })

  it('keeps instance and error unchanged on silent poll failure', async () => {
    vi.mocked(apiJson)
      .mockResolvedValueOnce(runningInstance)
      .mockRejectedValueOnce(new Error('Failed to fetch'))

    const eventId = ref(42)
    const { instance, error, load } = useHostedPi(eventId)

    await load()
    await load({ silent: true })

    expect(instance.value?.status).toBe('running')
    expect(error.value).toBe('')
  })

  it('clears instance and sets error on non-silent load failure', async () => {
    vi.mocked(apiJson)
      .mockResolvedValueOnce(runningInstance)
      .mockRejectedValueOnce(new Error('Failed to fetch'))

    const eventId = ref(42)
    const { instance, error, load } = useHostedPi(eventId)

    await load()
    await load()

    expect(instance.value).toBeNull()
    expect(error.value).toBe(i18n.global.t('hostedPi.unavailable'))
  })

  it('recovers instance and clears error on successful silent poll', async () => {
    vi.mocked(apiJson)
      .mockRejectedValueOnce(new Error('Failed to fetch'))
      .mockResolvedValueOnce(runningInstance)

    const eventId = ref(42)
    const { instance, error, load } = useHostedPi(eventId)

    await load()
    expect(instance.value).toBeNull()
    expect(error.value).toBe(i18n.global.t('hostedPi.unavailable'))

    await load({ silent: true })

    expect(instance.value?.status).toBe('running')
    expect(error.value).toBe('')
  })

  it('uses parsed API error detail on non-silent HTTP failure', async () => {
    const err = Object.assign(new Error('Hosted Pi konnte nicht gestartet werden.'), { status: 502 })
    vi.mocked(apiJson).mockRejectedValue(err)

    const eventId = ref(42)
    const { instance, error, load } = useHostedPi(eventId)

    await load()

    expect(instance.value).toBeNull()
    expect(error.value).toBe('Hosted Pi konnte nicht gestartet werden.')
  })
})
