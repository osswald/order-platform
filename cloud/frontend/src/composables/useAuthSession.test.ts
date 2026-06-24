import { beforeEach, describe, expect, it, vi } from 'vitest'

const mockRoute = {
  query: {} as Record<string, unknown>,
  name: 'dashboard' as string | symbol | null | undefined,
  meta: {} as Record<string, unknown>,
  params: {} as Record<string, unknown>,
  path: '/dashboard',
}

const mockReplace = vi.fn()

vi.mock('vue-router', () => ({
  useRoute: () => mockRoute,
  useRouter: () => ({ replace: mockReplace }),
}))

vi.mock('../api', () => ({
  apiFetch: vi.fn(),
  apiJson: vi.fn(),
  clearAuthStorage: vi.fn(),
}))

import { useAuthSession } from './useAuthSession'

describe('useAuthSession', () => {
  let assignSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    mockRoute.query = {}
    mockRoute.name = 'dashboard'
    mockRoute.path = '/dashboard'
    assignSpy = vi.spyOn(window.location, 'assign').mockImplementation(() => {})
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

  it('initializes activeOrganisationId from localStorage', () => {
    localStorage.setItem('access_token', 'test-token')
    localStorage.setItem('active_organisation_id', '5')

    const { activeOrganisationId } = useAuthSession()
    expect(activeOrganisationId.value).toBe(5)
  })

  it('setActiveOrganisation persists to localStorage and hard-reloads current path', () => {
    localStorage.setItem('access_token', 'test-token')
    localStorage.setItem('user_role', 'tenant_admin')
    mockRoute.path = '/dashboard'

    const { setActiveOrganisation } = useAuthSession()
    setActiveOrganisation(7)

    expect(localStorage.getItem('active_organisation_id')).toBe('7')
    expect(assignSpy).toHaveBeenCalledWith('/dashboard')
    expect(mockReplace).not.toHaveBeenCalled()
  })

  it('setActiveOrganisation on detail route reloads parent list path', () => {
    localStorage.setItem('access_token', 'test-token')
    localStorage.setItem('user_role', 'tenant_admin')
    mockRoute.name = 'events-detail'
    mockRoute.path = '/events/123'

    const { setActiveOrganisation } = useAuthSession()
    setActiveOrganisation(2)

    expect(localStorage.getItem('active_organisation_id')).toBe('2')
    expect(assignSpy).toHaveBeenCalledWith('/events')
  })

  it('setActiveHireCompany persists and hard-reloads for platform admin', () => {
    localStorage.setItem('access_token', 'test-token')
    localStorage.setItem('user_role', 'platform_admin')
    localStorage.setItem('is_admin', 'true')
    mockRoute.path = '/events'

    const { setActiveHireCompany } = useAuthSession()
    setActiveHireCompany(9)

    expect(localStorage.getItem('active_hire_company_id')).toBe('9')
    expect(assignSpy).toHaveBeenCalledWith('/events')
  })

  it('setActiveHireCompany is a no-op for tenant admin', () => {
    localStorage.setItem('access_token', 'test-token')
    localStorage.setItem('user_role', 'tenant_admin')

    const { setActiveHireCompany } = useAuthSession()
    setActiveHireCompany(9)

    expect(localStorage.getItem('active_hire_company_id')).toBeNull()
    expect(assignSpy).not.toHaveBeenCalled()
  })
})
