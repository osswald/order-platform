<template>
  <aside class="sidebar">
    <AppNavMenu
      :is-platform-admin="isPlatformAdmin"
      :can-access-tenant-admin="canAccessTenantAdmin"
      :can-access-organisation-settings="canAccessOrganisationSettings"
      :can-access-users="canAccessUsers"
      :is-tenant-admin-role="isTenantAdminRole"
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
  canAccessOrganisationSettings: { type: Boolean, default: false },
  canAccessUsers: { type: Boolean, default: false },
  isTenantAdminRole: { type: Boolean, default: false },
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
  background: rgb(var(--v-theme-surface));
  padding: 1rem 1rem 1rem 1.25rem;
  height: 100%;
  overflow-y: auto;
  border-right: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}
</style>
