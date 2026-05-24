<template>
  <RouterView v-if="authReady && !isLoggedIn" />
  <div v-else-if="authReady" class="app-layout">
    <Header :user-email="userEmail" @logout="handleLogout" />
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
import Header from './components/Header.vue'
import Sidebar from './components/Sidebar.vue'
import { useAuthSession } from './composables/useAuthSession'

const {
  isLoggedIn,
  authReady,
  userEmail,
  isAdmin,
  accessibleOrganisations,
  activeOrganisationId,
  setActiveOrganisation,
  handleLogout,
} = useAuthSession()
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
