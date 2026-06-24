import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import { i18n } from '../i18n'

vi.mock('../api', () => ({
  apiFetch: vi.fn(),
}))

import { apiFetch } from '../api'
import { useHostedPi } from './useHostedPi'

const runningInstance = {
  id: 1,
  event_id: 42,
  status: 'running',
  url: 'https://abc.demo.vendiqo.ch',
  expires_at: '2026-06-25T12:00:00Z',
}

function okJson(data) {
  return Promise.resolve({
    ok: true,
    status: 200,
    json: () => Promise.resolve(data),
  })
}

describe('useHostedPi', () => {
  beforeEach(() => {
    vi.mocked(apiFetch).mockReset()
  })

  it('loads a running instance on initial fetch', async () => {
    vi.mocked(apiFetch).mockImplementation(() => okJson(runningInstance))

    const eventId = ref(42)
    const { instance, error, load } = useHostedPi(eventId)

    await load()

    expect(apiFetch).toHaveBeenCalledWith('/events/42/hosted-pi')
    expect(instance.value?.status).toBe('running')
    expect(error.value).toBe('')
  })

  it('keeps instance and error unchanged on silent poll failure', async () => {
    vi.mocked(apiFetch)
      .mockImplementationOnce(() => okJson(runningInstance))
      .mockImplementationOnce(() => Promise.reject(new Error('Failed to fetch')))

    const eventId = ref(42)
    const { instance, error, load } = useHostedPi(eventId)

    await load()
    await load({ silent: true })

    expect(instance.value?.status).toBe('running')
    expect(error.value).toBe('')
  })

  it('clears instance and sets error on non-silent load failure', async () => {
    vi.mocked(apiFetch)
      .mockImplementationOnce(() => okJson(runningInstance))
      .mockImplementationOnce(() => Promise.reject(new Error('Failed to fetch')))

    const eventId = ref(42)
    const { instance, error, load } = useHostedPi(eventId)

    await load()
    await load()

    expect(instance.value).toBeNull()
    expect(error.value).toBe(i18n.global.t('hostedPi.unavailable'))
  })

  it('recovers instance and clears error on successful silent poll', async () => {
    vi.mocked(apiFetch)
      .mockImplementationOnce(() => Promise.reject(new Error('Failed to fetch')))
      .mockImplementationOnce(() => okJson(runningInstance))

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
    vi.mocked(apiFetch).mockImplementation(() =>
      Promise.resolve({
        ok: false,
        status: 502,
        text: () =>
          Promise.resolve(
            JSON.stringify({
              detail: { code: 'hosted_pi_start_failed', message: 'Hosted Pi konnte nicht gestartet werden.' },
            }),
          ),
      }),
    )

    const eventId = ref(42)
    const { instance, error, load } = useHostedPi(eventId)

    await load()

    expect(instance.value).toBeNull()
    expect(error.value).toBe('Hosted Pi konnte nicht gestartet werden.')
  })
})
