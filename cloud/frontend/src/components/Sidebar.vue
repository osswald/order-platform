<template>
  <aside class="sidebar">
    <AppNavMenu
      :is-platform-admin="isPlatformAdmin"
      :can-access-tenant-admin="canAccessTenantAdmin"
      :hire-companies="hireCompanies"
      :active-hire-company-id="activeHireCompanyId"
      :show-hire-company-picker="showHireCompanyPicker"
      :organisations="organisations"
      :active-organisation-id="activeOrganisationId"
      @change-organisation="$emit('change-organisation', $event)"
      @change-hire-company="$emit('change-hire-company', $event)"
    />
  </aside>
</template>

<script setup>
import AppNavMenu from './AppNavMenu.vue'

defineProps({
  isPlatformAdmin: { type: Boolean, default: false },
  canAccessTenantAdmin: { type: Boolean, default: false },
  hireCompanies: { type: Array, default: () => [] },
  activeHireCompanyId: { type: Number, default: null },
  showHireCompanyPicker: { type: Boolean, default: false },
  organisations: { type: Array, default: () => [] },
  activeOrganisationId: { type: Number, default: null },
})

defineEmits(['change-organisation', 'change-hire-company'])
</script>

<style scoped>
.sidebar {
  width: 280px;
  flex-shrink: 0;
  background: var(--p-surface-card);
  color: var(--p-text-color);
  padding: 1.25rem 0;
  height: calc(100vh - 64px);
  overflow-y: auto;
  border-right: 1px solid var(--p-content-border-color);
}

.sidebar::-webkit-scrollbar {
  width: 6px;
}

.sidebar::-webkit-scrollbar-track {
  background: transparent;
}

.sidebar::-webkit-scrollbar-thumb {
  background: var(--p-content-border-color);
  border-radius: 3px;
}

.sidebar::-webkit-scrollbar-thumb:hover {
  background: var(--p-text-muted-color);
}
</style>
