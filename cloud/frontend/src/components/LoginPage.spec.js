import { describe, expect, it, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import LoginPage from './LoginPage.vue'
import { vuetifyStubs } from '../../tests/helpers/vuetifyStub.js'
import { validateForm } from '../utils/formRules.js'

vi.mock('../composables/useAppVersion', () => ({
  useAppVersion: () => ({ label: 'test' }),
}))

vi.mock('../utils/formRules.js', async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    validateForm: vi.fn(),
  }
})

describe('LoginPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    localStorage.clear()
    validateForm.mockResolvedValue(false)
  })

  async function mountLogin() {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/', component: LoginPage }],
    })
    const wrapper = mount(LoginPage, {
      global: {
        plugins: [router],
        stubs: vuetifyStubs(),
      },
    })
    await router.isReady()
    return wrapper
  }

  it('does not call fetch when validation fails', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    const wrapper = await mountLogin()
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()
    expect(validateForm).toHaveBeenCalled()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('stores token after successful login', async () => {
    validateForm.mockResolvedValue(true)
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({
        access_token: 'test-token',
        is_admin: true,
        is_tenant_admin: false,
      }),
    })

    const wrapper = await mountLogin()
    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('admin@example.com')
    await inputs[1].setValue('secret')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(localStorage.getItem('access_token')).toBe('test-token')
    expect(localStorage.getItem('user_email')).toBe('admin@example.com')
  })
})
