import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {}, name: 'dashboard', meta: {}, params: {} }),
  useRouter: () => ({ replace: vi.fn() }),
}))

vi.mock('../api', () => ({
  apiFetch: vi.fn(),
  clearAuthStorage: vi.fn(),
}))

import { useAuthSession } from './useAuthSession'

describe('useAuthSession', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('canAccessUsers is true for tenant admin', () => {
    localStorage.setItem('access_token', 'test-token')
    localStorage.setItem('user_role', 'tenant_admin')
    localStorage.setItem('user_hire_company_id', '1')

    const { canAccessUsers, isLoggedIn } = useAuthSession()
    expect(isLoggedIn.value).toBe(true)
    expect(canAccessUsers.value).toBe(true)
  })

  it('canAccessUsers is false for plain member', () => {
    localStorage.setItem('access_token', 'test-token')
    localStorage.setItem('user_role', 'member')

    const { canAccessUsers } = useAuthSession()
    expect(canAccessUsers.value).toBe(false)
  })
})
