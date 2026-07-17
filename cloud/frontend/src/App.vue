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
          :can-access-organisation-settings="canAccessOrganisationSettings"
          :can-access-users="canAccessUsers"
          :is-tenant-admin-role="isTenantAdminRole"
          :hire-companies="hireCompanies"
          :active-hire-company-id="activeHireCompanyIdForViews ?? undefined"
          :show-hire-company-picker="isPlatformAdmin"
          :organisations="accessibleOrganisations"
          :active-organisation-id="activeOrganisationIdForViews ?? undefined"
          @change-organisation="setActiveOrganisation"
          @change-hire-company="setActiveHireCompany"
        />
        <main class="main-content" :class="{ 'main-content--mobile': isMobile }">
          <RouterView v-slot="{ Component }">
            <component
              :is="Component"
              :is-admin="isAdmin"
              :is-tenant-admin="isTenantAdminRole"
              :is-organisation-admin="isOrganisationAdminRole"
              :can-access-tenant-admin="canAccessTenantAdmin"
              :active-hire-company-id="activeHireCompanyIdForViews"
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
            :can-access-organisation-settings="canAccessOrganisationSettings"
            :can-access-users="canAccessUsers"
            :is-tenant-admin-role="isTenantAdminRole"
            :hire-companies="hireCompanies"
            :active-hire-company-id="activeHireCompanyIdForViews ?? undefined"
            :show-hire-company-picker="isPlatformAdmin"
            :organisations="accessibleOrganisations"
            :active-organisation-id="activeOrganisationIdForViews ?? undefined"
            @change-organisation="setActiveOrganisation"
            @change-hire-company="setActiveHireCompany"
            @navigate="mobileNavOpen = false"
          />
        </div>
      </v-navigation-drawer>
    </div>
  </v-app>
</template>

<script setup lang="ts">
import { computed, provide, ref, unref, watch } from 'vue'
import { useRoute } from 'vue-router'
import Header from './components/Header.vue'
import Sidebar from './components/Sidebar.vue'
import AppNavMenu from './components/AppNavMenu.vue'
import { useAuthSession } from './composables/useAuthSession'
import { useBreakpoint } from './composables/useBreakpoint'
import { useThemePreference } from './composables/useThemePreference'
import { MOBILE_BREAKPOINT } from './constants/layout'
import { SESSION_CONTEXT_KEY } from './sessionContext'
import { normalizeOrganisationId } from './utils/orgId'

const { matches: isMobile } = useBreakpoint(MOBILE_BREAKPOINT)
useThemePreference()
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
  canAccessOrganisationSettings,
  canAccessUsers,
  isTenantAdminRole,
  isOrganisationAdminRole,
  hireCompanies,
  activeHireCompanyId,
  setActiveHireCompany,
  accessibleOrganisations,
  activeOrganisationId,
  setActiveOrganisation,
  handleLogout,
  reloadHireCompaniesAndSelect,
  reloadOrganisationsAndSelect,
  fetchAccessibleOrganisations,
} = useAuthSession()

const activeOrganisationIdForViews = computed(() =>
  normalizeOrganisationId(unref(activeOrganisationId)),
)

const activeHireCompanyIdForViews = computed(() =>
  normalizeOrganisationId(unref(activeHireCompanyId)),
)

provide(SESSION_CONTEXT_KEY, {
  reloadHireCompaniesAndSelect,
  reloadOrganisationsAndSelect,
  accessibleOrganisations,
  fetchAccessibleOrganisations,
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

@media (max-width: 992px) {
  .main-content {
    overflow-x: hidden;
  }
}
</style>
