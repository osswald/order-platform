<template>
  <aside class="sidebar">
    <AppNavMenu
      :is-admin="isAdmin"
      :organisations="organisations"
      :active-organisation-id="activeOrganisationId"
      @change-organisation="$emit('change-organisation', $event)"
    />
  </aside>
</template>

<script setup>
import AppNavMenu from './AppNavMenu.vue'

defineProps({
  isAdmin: {
    type: Boolean,
    default: false,
  },
  organisations: {
    type: Array,
    default: () => [],
  },
  activeOrganisationId: {
    type: Number,
    default: null,
  },
})

defineEmits(['change-organisation'])
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
