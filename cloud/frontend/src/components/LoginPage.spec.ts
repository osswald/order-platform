import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import LoginPage from './LoginPage.vue'
import { vuetifyStubs } from '../../tests/helpers/vuetifyStub.js'
import { validateForm } from '../utils/formRules.js'

vi.mock('../composables/useAppVersion', () => ({
  useAppVersion: () => ({ label: 'test' }),
}))

vi.mock('../utils/formRules.js', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../utils/formRules.js')>()
  return {
    ...actual,
    validateForm: vi.fn(),
  }
})

describe('LoginPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    localStorage.clear()
    vi.mocked(validateForm).mockResolvedValue(false)
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  async function mountLogin(query: Record<string, string> = {}) {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/', component: LoginPage }],
    })
    await router.push({ path: '/', query })
    const wrapper = mount(LoginPage, {
      global: {
        plugins: [router],
        stubs: vuetifyStubs(),
      },
    })
    await router.isReady()
    return wrapper
  }

  function captureLocationHref(): string[] {
    const assigned: string[] = []
    Object.defineProperty(window.location, 'href', {
      configurable: true,
      get: () => 'http://localhost:3000/',
      set: (value: string) => {
        assigned.push(value)
      },
    })
    return assigned
  }

  async function submitSuccessfulLogin(query: Record<string, string> = {}) {
    vi.useFakeTimers()
    vi.mocked(validateForm).mockResolvedValue(true)
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({
        access_token: 'test-token',
        is_admin: true,
        is_tenant_admin: false,
      }),
    } as Response)
    const assigned = captureLocationHref()
    const wrapper = await mountLogin(query)
    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('admin@example.com')
    await inputs[1].setValue('secret')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()
    await vi.advanceTimersByTimeAsync(500)
    return assigned
  }

  it('uses outlined primary intent for the submit CTA', async () => {
    const wrapper = await mountLogin()
    const submit = wrapper.findAll('button').find((btn) => btn.attributes('data-color') === 'primary')
    expect(submit).toBeTruthy()
    const variant = submit!.attributes('data-variant')
    expect(variant === undefined || variant === '' || variant === 'outlined').toBe(true)
    expect(variant).not.toBe('text')
    expect(variant).not.toBe('flat')
  })

  it('does not call fetch when validation fails', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    const wrapper = await mountLogin()
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()
    expect(validateForm).toHaveBeenCalled()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('stores token after successful login', async () => {
    vi.mocked(validateForm).mockResolvedValue(true)
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({
        access_token: 'test-token',
        is_admin: true,
        is_tenant_admin: false,
      }),
    } as Response)

    const wrapper = await mountLogin()
    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('admin@example.com')
    await inputs[1].setValue('secret')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(localStorage.getItem('auth_session')).toBe('1')
    expect(localStorage.getItem('access_token')).toBeNull()
    expect(localStorage.getItem('user_email')).toBe('admin@example.com')
  })

  it('falls back to /dashboard for a protocol-relative redirect', async () => {
    const assigned = await submitSuccessfulLogin({ redirect: '//evil.example' })
    expect(assigned.length).toBeGreaterThan(0)
    expect(assigned.every((value) => value === '/dashboard')).toBe(true)
  })

  it('navigates to a same-origin relative redirect path', async () => {
    const assigned = await submitSuccessfulLogin({ redirect: '/events' })
    expect(assigned.length).toBeGreaterThan(0)
    expect(assigned.every((value) => value === '/events')).toBe(true)
  })
})
