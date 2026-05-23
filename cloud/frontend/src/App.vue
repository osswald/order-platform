<template>
  <RouterView v-if="authReady && !isLoggedIn" />
  <div v-else-if="authReady" class="app-layout">
    <Header :userEmail="userEmail" @logout="handleLogout" />
    <div class="app-body">
      <Sidebar
        :is-admin="isAdmin"
        :organisations="accessibleOrganisations"
        :active-organisation-id="activeOrganisationId"
        @change-organisation="setActiveOrganisation"
      />
      <main class="main-content">
        <RouterView v-slot="{ Component }">
          <component
            :is="Component"
            :is-admin="isAdmin"
            :active-organisation-id="activeOrganisationId"
          />
        </RouterView>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { apiFetch } from './api'
import Header from './components/Header.vue'
import Sidebar from './components/Sidebar.vue'

const route = useRoute()
const router = useRouter()

const isLoggedIn = ref(!!localStorage.getItem('access_token'))
const authReady = ref(!isLoggedIn.value)
const userEmail = ref(localStorage.getItem('user_email') || '')
const isAdmin = ref(localStorage.getItem('is_admin') === 'true')
const accessibleOrganisations = ref([])
const activeOrganisationId = ref(parseOrganisationId(route.query.organisation))

function parseOrganisationId(value) {
  if (value == null || value === '') return null
  const id = Number(value)
  return Number.isFinite(id) ? id : null
}

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
    const r = await apiFetch('/auth/me')
    if (!r.ok) {
      isAdmin.value = false
      return false
    }
    const data = await r.json()
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
  } catch (e) {
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
  const exists = accessibleOrganisations.value.some((org) => Number(org.id) === Number(candidate))

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
    const r = await apiFetch('/events/organisations')
    if (!r.ok) {
      accessibleOrganisations.value = []
      syncActiveOrganisation()
      return
    }
    accessibleOrganisations.value = await r.json()
    syncActiveOrganisation()
    updateRouteOrganisation()
  } catch (e) {
    accessibleOrganisations.value = []
    syncActiveOrganisation()
  }
}

function setActiveOrganisation(id) {
  if (id == null || id === '') {
    activeOrganisationId.value = null
    localStorage.removeItem('active_organisation_id')
  } else {
    const n = Number(id)
    activeOrganisationId.value = Number.isFinite(n) ? n : null
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
  }
)

watch(
  () => route.name,
  () => {
    enforceRouteAccess()
    updateRouteOrganisation()
  }
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
    await apiFetch('/auth/logout', {
      method: 'POST',
    })
  } catch (e) {
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
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body, html {
  height: 100%;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  background: var(--p-surface-ground);
  color: var(--p-text-color);
}

#app {
  height: 100vh;
  overflow: hidden;
}

.app-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.app-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.main-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  background: var(--p-surface-ground);
}

.main-content::-webkit-scrollbar {
  width: 8px;
}

.main-content::-webkit-scrollbar-track {
  background: var(--p-surface-ground);
}

.main-content::-webkit-scrollbar-thumb {
  background: var(--p-content-border-color);
  border-radius: 4px;
}

.main-content::-webkit-scrollbar-thumb:hover {
  background: var(--p-text-muted-color);
}

.p-card {
  border-radius: 1rem;
}

.p-datatable .p-datatable-tbody > tr {
  cursor: pointer;
}

.p-button.danger {
  background: var(--p-red-500);
  border-color: var(--p-red-500);
  color: #fff;
}

.p-button.danger:hover {
  background: var(--p-red-600);
  border-color: var(--p-red-600);
}

.p-button.secondary-button {
  background: transparent;
  border-color: var(--p-content-border-color);
  color: var(--p-text-color);
}

.p-button.secondary-button:hover {
  background: var(--p-surface-hover);
  border-color: var(--p-content-border-color);
  color: var(--p-text-color);
}

.success,
.error {
  border-radius: var(--p-border-radius-md);
  padding: 0.875rem 1rem;
}

.success {
  background: var(--p-green-50);
  color: var(--p-green-700);
}

.error {
  background: var(--p-red-50);
  color: var(--p-red-700);
}
</style>
