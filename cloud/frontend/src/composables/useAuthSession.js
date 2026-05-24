import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { apiFetch } from '../api'

function parseOrganisationId(value) {
  if (value == null || value === '') return null
  const id = Number(value)
  return Number.isFinite(id) ? id : null
}

export function useAuthSession() {
  const route = useRoute()
  const router = useRouter()

  const isLoggedIn = ref(!!localStorage.getItem('access_token'))
  const authReady = ref(!isLoggedIn.value)
  const userEmail = ref(localStorage.getItem('user_email') || '')
  const isAdmin = ref(localStorage.getItem('is_admin') === 'true')
  const accessibleOrganisations = ref([])
  const activeOrganisationId = ref(parseOrganisationId(route.query.organisation))

  function updateRouteOrganisation() {
    if (!isLoggedIn.value || route.name === 'login') return

    const nextOrganisation =
      activeOrganisationId.value == null ? undefined : String(activeOrganisationId.value)
    const currentOrganisation = route.query.organisation

    if (currentOrganisation === nextOrganisation) return

    router.replace({
      name: route.name,
      params: route.params,
      query: {
        ...route.query,
        organisation: nextOrganisation,
      },
    })
  }

  async function syncSession() {
    const token = localStorage.getItem('access_token')
    if (!token) {
      isAdmin.value = false
      return false
    }
    try {
      const response = await apiFetch('/auth/me')
      if (!response.ok) {
        isAdmin.value = false
        return false
      }
      const data = await response.json()
      isAdmin.value = !!data.is_admin
      localStorage.setItem('is_admin', data.is_admin ? 'true' : 'false')
      if (data.id != null) {
        localStorage.setItem('user_id', String(data.id))
      }
      if (data.email) {
        userEmail.value = data.email
        localStorage.setItem('user_email', data.email)
      }
      return true
    } catch {
      isAdmin.value = false
      return false
    }
  }

  function syncActiveOrganisation() {
    if (!accessibleOrganisations.value.length) {
      activeOrganisationId.value = null
      localStorage.removeItem('active_organisation_id')
      return
    }

    const fromRoute = parseOrganisationId(route.query.organisation)
    const fromStorage = parseOrganisationId(localStorage.getItem('active_organisation_id'))
    const candidate = fromRoute ?? fromStorage ?? accessibleOrganisations.value[0].id
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
    try {
      const response = await apiFetch('/events/organisations')
      if (!response.ok) {
        accessibleOrganisations.value = []
        syncActiveOrganisation()
        return
      }
      accessibleOrganisations.value = await response.json()
      syncActiveOrganisation()
      updateRouteOrganisation()
    } catch {
      accessibleOrganisations.value = []
      syncActiveOrganisation()
    }
  }

  function setActiveOrganisation(id) {
    if (id == null || id === '') {
      activeOrganisationId.value = null
      localStorage.removeItem('active_organisation_id')
    } else {
      const parsed = Number(id)
      activeOrganisationId.value = Number.isFinite(parsed) ? parsed : null
      if (activeOrganisationId.value != null) {
        localStorage.setItem('active_organisation_id', String(activeOrganisationId.value))
      } else {
        localStorage.removeItem('active_organisation_id')
      }
    }
    updateRouteOrganisation()
  }

  function enforceRouteAccess() {
    if (!isLoggedIn.value || !route.meta.adminOnly || isAdmin.value) return
    router.replace({
      name: 'no-access',
      params: { section: route.name },
      query: route.query,
    })
  }

  watch(
    () => route.query.organisation,
    (organisation) => {
      if (!isLoggedIn.value) return
      const id = parseOrganisationId(organisation)
      if (id === activeOrganisationId.value) return

      if (id != null && accessibleOrganisations.value.some((org) => Number(org.id) === Number(id))) {
        activeOrganisationId.value = id
        localStorage.setItem('active_organisation_id', String(id))
        return
      }

      if (accessibleOrganisations.value.length) {
        syncActiveOrganisation()
        updateRouteOrganisation()
      }
    },
  )

  watch(
    () => route.name,
    () => {
      enforceRouteAccess()
      updateRouteOrganisation()
    },
  )

  onMounted(async () => {
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
      isAdmin.value = localStorage.getItem('is_admin') === 'true'
      activeOrganisationId.value = parseOrganisationId(route.query.organisation)
    })
  })

  async function handleLogout() {
    try {
      await apiFetch('/auth/logout', { method: 'POST' })
    } catch {
      // ignore
    }
    localStorage.removeItem('access_token')
    localStorage.removeItem('user_email')
    localStorage.removeItem('is_admin')
    localStorage.removeItem('user_id')
    localStorage.removeItem('active_organisation_id')
    accessibleOrganisations.value = []
    activeOrganisationId.value = null
    isLoggedIn.value = false
    userEmail.value = ''
    router.replace({ name: 'login' })
  }

  return {
    isLoggedIn,
    authReady,
    userEmail,
    isAdmin,
    accessibleOrganisations,
    activeOrganisationId,
    setActiveOrganisation,
    handleLogout,
  }
}
