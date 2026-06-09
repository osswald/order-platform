<template>
  <v-app>
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

      <v-navigation-drawer
        v-model="mobileNavOpen"
        temporary
        location="left"
        width="280"
      >
        <v-toolbar density="compact" :title="$t('common.menu')" />
        <div class="pa-3">
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
        </div>
      </v-navigation-drawer>
    </div>
  </v-app>
</template>

<script setup>
import { computed, provide, ref, unref, watch } from 'vue'
import { useRoute } from 'vue-router'
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

const activeOrganisationIdForViews = computed(() =>
  normalizeOrganisationId(unref(activeOrganisationId)),
)

provide(SESSION_CONTEXT_KEY, {
  reloadHireCompaniesAndSelect,
  reloadOrganisationsAndSelect,
})
</script>

<style>
@import './assets/vuetify-app.css';
@import './assets/responsive.css';

*,
*::before,
*::after {
  box-sizing: border-box;
}

html,
body {
  margin: 0;
  padding: 0;
  height: 100%;
}

#app {
  height: 100dvh;
}

.app-layout {
  display: flex;
  flex-direction: column;
  height: 100dvh;
}

.app-body {
  display: flex;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.main-content {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  overflow-x: hidden;
  background: rgb(var(--v-theme-background));
}

.main-content--mobile {
  width: 100%;
}

@media (max-width: 768px) {
  .main-content {
    overflow-x: auto;
  }
}
</style>
