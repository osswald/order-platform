<template>
  <RouterView v-if="authReady && !isLoggedIn" />
  <div v-else-if="authReady" class="app-layout">
    <Header
      :user-email="userEmail"
      :is-mobile="isMobile"
      @logout="handleLogout"
      @toggle-nav="mobileNavOpen = !mobileNavOpen"
    />
    <div class="app-body">
      <Sidebar
        v-if="!isMobile"
        :is-platform-admin="isPlatformAdmin"
        :can-access-tenant-admin="canAccessTenantAdmin"
        :hire-companies="hireCompanies"
        :active-hire-company-id="activeHireCompanyId"
        :show-hire-company-picker="isPlatformAdmin"
        :organisations="accessibleOrganisations"
        :active-organisation-id="activeOrganisationIdForViews"
        @change-organisation="setActiveOrganisation"
        @change-hire-company="setActiveHireCompany"
      />
      <main class="main-content" :class="{ 'main-content--mobile': isMobile }">
        <RouterView v-slot="{ Component }">
          <component
            :is="Component"
            :is-admin="isAdmin"
            :active-organisation-id="activeOrganisationIdForViews"
          />
        </RouterView>
      </main>
    </div>

    <Drawer
      v-model:visible="mobileNavOpen"
      position="left"
      :modal="true"
      :dismissable="true"
      header="Menü"
      class="mobile-nav-drawer"
    >
      <AppNavMenu
        :is-platform-admin="isPlatformAdmin"
        :can-access-tenant-admin="canAccessTenantAdmin"
        :hire-companies="hireCompanies"
        :active-hire-company-id="activeHireCompanyId"
        :show-hire-company-picker="isPlatformAdmin"
        :organisations="accessibleOrganisations"
        :active-organisation-id="activeOrganisationIdForViews"
        @change-organisation="setActiveOrganisation"
        @change-hire-company="setActiveHireCompany"
        @navigate="mobileNavOpen = false"
      />
    </Drawer>
  </div>
</template>

<script setup>
import { computed, provide, ref, unref, watch } from 'vue'
import { useRoute } from 'vue-router'
import Drawer from 'primevue/drawer'
import Header from './components/Header.vue'
import Sidebar from './components/Sidebar.vue'
import AppNavMenu from './components/AppNavMenu.vue'
import { useAuthSession } from './composables/useAuthSession'
import { useBreakpoint } from './composables/useBreakpoint'
import { SESSION_CONTEXT_KEY } from './sessionContext'
import { normalizeOrganisationId } from './utils/orgId'

const MOBILE_BREAKPOINT = 992

const { matches: isMobile } = useBreakpoint(MOBILE_BREAKPOINT)
const mobileNavOpen = ref(false)
const route = useRoute()

watch(
  () => route.fullPath,
  () => {
    mobileNavOpen.value = false
  },
)

watch(isMobile, (mobile) => {
  if (!mobile) {
    mobileNavOpen.value = false
  }
})

const {
  isLoggedIn,
  authReady,
  userEmail,
  isAdmin,
  isPlatformAdmin,
  canAccessTenantAdmin,
  hireCompanies,
  activeHireCompanyId,
  setActiveHireCompany,
  accessibleOrganisations,
  activeOrganisationId,
  setActiveOrganisation,
  handleLogout,
  reloadHireCompaniesAndSelect,
  reloadOrganisationsAndSelect,
} = useAuthSession()

/** Unwrap ref for dynamic <component> props (avoids passing Ref / object to children). */
const activeOrganisationIdForViews = computed(() =>
  normalizeOrganisationId(unref(activeOrganisationId)),
)

provide(SESSION_CONTEXT_KEY, {
  reloadHireCompaniesAndSelect,
  reloadOrganisationsAndSelect,
})
</script>

<style>
@import './assets/responsive.css';

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
  min-width: 0;
  overflow-y: auto;
  overflow-x: hidden;
  background: var(--p-surface-ground);
}

.main-content--mobile {
  width: 100%;
}

.mobile-nav-drawer {
  width: min(280px, 85vw);
}

.mobile-nav-drawer :deep(.p-drawer-content) {
  padding: 1.25rem 0;
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
