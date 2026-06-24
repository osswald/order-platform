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

<script setup lang="ts">
import AppNavMenu from './AppNavMenu.vue'
import type { HireCompanyBrief, OrganisationRead } from '@/types/api'

withDefaults(
  defineProps<{
    isPlatformAdmin?: boolean
    canAccessTenantAdmin?: boolean
    canAccessOrganisationSettings?: boolean
    canAccessUsers?: boolean
    isTenantAdminRole?: boolean
    hireCompanies?: HireCompanyBrief[]
    activeHireCompanyId?: number | null
    showHireCompanyPicker?: boolean
    organisations?: OrganisationRead[]
    activeOrganisationId?: number | null
  }>(),
  {
    isPlatformAdmin: false,
    canAccessTenantAdmin: false,
    canAccessOrganisationSettings: false,
    canAccessUsers: false,
    isTenantAdminRole: false,
    hireCompanies: () => [],
    activeHireCompanyId: null,
    showHireCompanyPicker: false,
    organisations: () => [],
    activeOrganisationId: null,
  },
)

defineEmits<{
  'change-organisation': [id: number | null]
  'change-hire-company': [id: number | null]
}>()
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
