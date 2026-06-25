import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { apiFetch, apiJson, clearAuthStorage } from '@/api'
import { normalizeOrganisationId } from '@/utils/orgId'
import {
  readLegacyOrganisationQuery,
  resolveContextReloadPath,
} from '@/utils/contextReload'
import { isApiError } from '@/types/api'
import type { AuthMeResponse, HireCompanyBrief, OrganisationRead } from '@/types/api'
import { syncThemeFromAuthMe } from './useThemePreference'

const ROLE_PLATFORM = 'platform_admin'
const ROLE_TENANT_ADMIN = 'tenant_admin'
const ROLE_ORGANISATION_ADMIN = 'organisation_admin'
const ROLE_MEMBER = 'member'

function parseId(value: unknown): number | null {
  return normalizeOrganisationId(value)
}

export function useAuthSession() {
  const route = useRoute()
  const router = useRouter()

  const isLoggedIn = ref(!!localStorage.getItem('access_token'))
  const authReady = ref(!isLoggedIn.value)
  const userEmail = ref(localStorage.getItem('user_email') || '')
  const userRole = ref(localStorage.getItem('user_role') || ROLE_MEMBER)
  const isPlatformAdmin = ref(localStorage.getItem('is_admin') === 'true')
  const isTenantAdmin = ref(localStorage.getItem('is_tenant_admin') === 'true')
  const isOrganisationAdmin = ref(localStorage.getItem('is_organisation_admin') === 'true')
  const userHireCompanyId = ref(parseId(localStorage.getItem('user_hire_company_id')))
  const hireCompanies = ref<HireCompanyBrief[]>([])
  const activeHireCompanyId = ref(parseId(localStorage.getItem('active_hire_company_id')))
  const accessibleOrganisations = ref<OrganisationRead[]>([])
  const activeOrganisationId = ref(parseId(localStorage.getItem('active_organisation_id')))

  const isAdmin = computed(() => isPlatformAdmin.value)
  const isTenantAdminRole = computed(() => userRole.value === ROLE_TENANT_ADMIN)
  const isOrganisationAdminRole = computed(() => userRole.value === ROLE_ORGANISATION_ADMIN)
  const canAccessTenantAdmin = computed(
    () =>
      userRole.value === ROLE_TENANT_ADMIN ||
      (isPlatformAdmin.value && activeHireCompanyId.value != null),
  )
  const canAccessOrganisationSettings = computed(
    () => canAccessTenantAdmin.value || isOrganisationAdminRole.value,
  )
  const canAccessUsers = computed(
    () => canAccessTenantAdmin.value || isOrganisationAdminRole.value,
  )

  function reloadAfterContextChange() {
    const path = resolveContextReloadPath(
      route.name == null ? null : String(route.name),
      route.path,
    )
    window.location.assign(path)
  }

  function migrateLegacyOrganisationQuery() {
    const fromQuery = readLegacyOrganisationQuery(route.query as Record<string, unknown>)
    if (fromQuery == null) return

    activeOrganisationId.value = fromQuery
    localStorage.setItem('active_organisation_id', String(fromQuery))

    const { organisation: _organisation, ...rest } = route.query
    void router.replace({ path: route.path, query: rest })
  }

  function syncActiveHireCompany() {
    if (userRole.value === ROLE_TENANT_ADMIN && userHireCompanyId.value != null) {
      activeHireCompanyId.value = userHireCompanyId.value
      localStorage.setItem('active_hire_company_id', String(userHireCompanyId.value))
      return
    }
    if (!isPlatformAdmin.value) {
      activeHireCompanyId.value = null
      localStorage.removeItem('active_hire_company_id')
      return
    }
    if (!hireCompanies.value.length) {
      activeHireCompanyId.value = null
      localStorage.removeItem('active_hire_company_id')
      return
    }
    const fromStorage = parseId(localStorage.getItem('active_hire_company_id'))
    const exists = hireCompanies.value.some((c) => Number(c.id) === Number(fromStorage))
    const next = exists ? fromStorage : hireCompanies.value[0].id
    activeHireCompanyId.value = next
    localStorage.setItem('active_hire_company_id', String(next))
  }

  function setActiveHireCompany(id: number | string | null | undefined) {
    if (userRole.value === ROLE_TENANT_ADMIN) return
    const parsed = parseId(id)
    if (parsed === activeHireCompanyId.value) return
    activeHireCompanyId.value = parsed
    if (parsed != null) {
      localStorage.setItem('active_hire_company_id', String(parsed))
    } else {
      localStorage.removeItem('active_hire_company_id')
    }
    reloadAfterContextChange()
  }

  function applySessionData(data: AuthMeResponse) {
    isPlatformAdmin.value = !!data.is_admin
    userRole.value = data.role || (data.is_admin ? ROLE_PLATFORM : ROLE_MEMBER)
    isTenantAdmin.value = !!data.is_tenant_admin
    isOrganisationAdmin.value = !!data.is_organisation_admin
    userHireCompanyId.value = parseId(data.hire_company_id)
    localStorage.setItem('is_admin', data.is_admin ? 'true' : 'false')
    localStorage.setItem('user_role', userRole.value)
    localStorage.setItem('is_tenant_admin', data.is_tenant_admin ? 'true' : 'false')
    localStorage.setItem(
      'is_organisation_admin',
      data.is_organisation_admin ? 'true' : 'false',
    )
    if (data.hire_company_id != null) {
      localStorage.setItem('user_hire_company_id', String(data.hire_company_id))
    } else {
      localStorage.removeItem('user_hire_company_id')
    }
    if (data.email) {
      userEmail.value = data.email
      localStorage.setItem('user_email', data.email)
    }
    if (data.id != null) {
      localStorage.setItem('user_id', String(data.id))
    }
    hireCompanies.value = Array.isArray(data.hire_companies) ? data.hire_companies : []
    syncActiveHireCompany()
    syncThemeFromAuthMe(data)
  }

  async function syncSession(): Promise<boolean> {
    const token = localStorage.getItem('access_token')
    if (!token) {
      isPlatformAdmin.value = false
      isTenantAdmin.value = false
      isOrganisationAdmin.value = false
      return false
    }
    try {
      const data = await apiJson<AuthMeResponse>('/auth/me')
      applySessionData(data)
      return true
    } catch (err: unknown) {
      isPlatformAdmin.value = false
      isTenantAdmin.value = false
      isOrganisationAdmin.value = false
      if (isApiError(err) && err.status === 401) {
        clearAuthStorage()
      }
      return false
    }
  }

  function syncActiveOrganisation() {
    if (!accessibleOrganisations.value.length) {
      activeOrganisationId.value = null
      localStorage.removeItem('active_organisation_id')
      return
    }

    const fromStorage = parseId(localStorage.getItem('active_organisation_id'))
    const candidate = fromStorage ?? accessibleOrganisations.value[0].id
    const exists = accessibleOrganisations.value.some(
      (org) => Number(org.id) === Number(candidate),
    )

    activeOrganisationId.value = exists ? candidate : accessibleOrganisations.value[0].id
    localStorage.setItem('active_organisation_id', String(activeOrganisationId.value))
  }

  async function fetchAccessibleOrganisations() {
    const token = localStorage.getItem('access_token')
    if (!token) {
      accessibleOrganisations.value = []
      syncActiveOrganisation()
      return
    }
    if (isPlatformAdmin.value && activeHireCompanyId.value == null) {
      accessibleOrganisations.value = []
      syncActiveOrganisation()
      return
    }
    try {
      accessibleOrganisations.value = await apiJson<OrganisationRead[]>('/events/organisations')
      syncActiveOrganisation()
    } catch {
      accessibleOrganisations.value = []
      syncActiveOrganisation()
    }
  }

  function setActiveOrganisation(id: number | string | null | undefined) {
    const parsed = normalizeOrganisationId(id)
    if (parsed === activeOrganisationId.value) return
    activeOrganisationId.value = parsed
    if (parsed != null) {
      localStorage.setItem('active_organisation_id', String(parsed))
    } else {
      localStorage.removeItem('active_organisation_id')
    }
    reloadAfterContextChange()
  }

  function enforceRouteAccess() {
    if (!isLoggedIn.value) return
    const section = route.name == null ? '' : String(route.name)
    if (route.meta.platformOnly && !isPlatformAdmin.value) {
      router.replace({
        name: 'no-access',
        params: { section },
        query: route.query,
      })
      return
    }
    if (route.meta.tenantAdminOnly && !canAccessTenantAdmin.value) {
      router.replace({
        name: 'no-access',
        params: { section },
        query: route.query,
      })
      return
    }
    if (route.meta.organisationManagerOnly && !canAccessOrganisationSettings.value) {
      router.replace({
        name: 'no-access',
        params: { section },
        query: route.query,
      })
      return
    }
    if (route.meta.usersOnly && !canAccessUsers.value) {
      router.replace({
        name: 'no-access',
        params: { section },
        query: route.query,
      })
    }
  }

  watch(
    () => route.name,
    () => {
      enforceRouteAccess()
    },
  )

  onMounted(async () => {
    migrateLegacyOrganisationQuery()

    if (isLoggedIn.value) {
      const ok = await syncSession()
      if (!ok) {
        isLoggedIn.value = false
        authReady.value = true
        router.replace({ name: 'login' })
        return
      }
      await fetchAccessibleOrganisations()
      enforceRouteAccess()
    }
    authReady.value = true

    window.addEventListener('storage', () => {
      isLoggedIn.value = !!localStorage.getItem('access_token')
      userEmail.value = localStorage.getItem('user_email') || ''
      isPlatformAdmin.value = localStorage.getItem('is_admin') === 'true'
      userRole.value = localStorage.getItem('user_role') || ROLE_MEMBER
      isTenantAdmin.value = localStorage.getItem('is_tenant_admin') === 'true'
      isOrganisationAdmin.value = localStorage.getItem('is_organisation_admin') === 'true'
      activeOrganisationId.value = parseId(localStorage.getItem('active_organisation_id'))
      activeHireCompanyId.value = parseId(localStorage.getItem('active_hire_company_id'))
    })
  })

  async function reloadHireCompaniesAndSelect(companyId: number | null = null) {
    await syncSession()
    if (companyId != null) {
      setActiveHireCompany(companyId)
    }
  }

  async function reloadOrganisationsAndSelect(organisationId: number | null = null) {
    if (organisationId != null) {
      activeOrganisationId.value = organisationId
      localStorage.setItem('active_organisation_id', String(organisationId))
      reloadAfterContextChange()
      return
    }
    await fetchAccessibleOrganisations()
  }

  async function handleLogout() {
    try {
      await apiFetch('/auth/logout', { method: 'POST' })
    } catch {
      // ignore
    }
    clearAuthStorage()
    accessibleOrganisations.value = []
    hireCompanies.value = []
    activeOrganisationId.value = null
    activeHireCompanyId.value = null
    isOrganisationAdmin.value = false
    isLoggedIn.value = false
    userEmail.value = ''
    router.replace({ name: 'login' })
  }

  return {
    isLoggedIn,
    authReady,
    userEmail,
    isAdmin,
    isPlatformAdmin,
    isTenantAdmin,
    isOrganisationAdmin,
    isTenantAdminRole,
    isOrganisationAdminRole,
    userRole,
    canAccessTenantAdmin,
    canAccessOrganisationSettings,
    canAccessUsers,
    hireCompanies,
    activeHireCompanyId,
    setActiveHireCompany,
    accessibleOrganisations,
    activeOrganisationId,
    setActiveOrganisation,
    handleLogout,
    fetchAccessibleOrganisations,
    reloadHireCompaniesAndSelect,
    reloadOrganisationsAndSelect,
  }
}
