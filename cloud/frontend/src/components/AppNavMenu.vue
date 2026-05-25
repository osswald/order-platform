<template>
  <nav class="nav-menu">
    <div class="organisation-context">
      <label>Aktive Organisation</label>
      <Select
        :modelValue="activeOrganisationId"
        :options="organisationOptions"
        optionLabel="name"
        optionValue="id"
        placeholder="Keine Organisation"
        :disabled="organisationOptions.length <= 1"
        @update:modelValue="changeOrganisation"
      />
    </div>

    <div class="nav-section">
      <h3 class="section-title">HAUPTMENÜ</h3>
      <ul class="menu-items">
        <li>
          <RouterLink :to="routeTo('dashboard')" class="menu-item" @click="onNavigate">
            <i class="icon pi pi-chart-line"></i>
            <span class="label">Dashboard</span>
          </RouterLink>
        </li>
        <li>
          <RouterLink :to="routeTo('events')" class="menu-item" @click="onNavigate">
            <i class="icon pi pi-calendar"></i>
            <span class="label">Veranstaltungen</span>
          </RouterLink>
        </li>
        <li>
          <RouterLink :to="routeTo('waiters')" class="menu-item" @click="onNavigate">
            <i class="icon pi pi-id-card"></i>
            <span class="label">Kellner</span>
          </RouterLink>
        </li>
        <li>
          <RouterLink :to="routeTo('articles')" class="menu-item" @click="onNavigate">
            <i class="icon pi pi-tags"></i>
            <span class="label">Artikel</span>
          </RouterLink>
        </li>
        <li>
          <RouterLink :to="routeTo('article-categories')" class="menu-item" @click="onNavigate">
            <i class="icon pi pi-folder"></i>
            <span class="label">Artikelkategorien</span>
          </RouterLink>
        </li>
        <li>
          <RouterLink :to="routeTo('appliance-lendings')" class="menu-item" @click="onNavigate">
            <i class="icon pi pi-calendar-plus"></i>
            <span class="label">Geräteausleihen</span>
          </RouterLink>
        </li>
      </ul>
    </div>

    <div class="nav-section">
      <h3 class="section-title">VERWALTUNG</h3>
      <ul class="menu-items">
        <li v-if="isAdmin">
          <RouterLink :to="routeTo('organisations')" class="menu-item" @click="onNavigate">
            <i class="icon pi pi-building"></i>
            <span class="label">Organisationen</span>
          </RouterLink>
        </li>
        <li v-if="isAdmin">
          <RouterLink :to="routeTo('appliances')" class="menu-item" @click="onNavigate">
            <i class="icon pi pi-desktop"></i>
            <span class="label">Geräte</span>
          </RouterLink>
        </li>
        <li v-if="isAdmin">
          <RouterLink :to="routeTo('users')" class="menu-item" @click="onNavigate">
            <i class="icon pi pi-user"></i>
            <span class="label">Benutzer</span>
          </RouterLink>
        </li>
        <li>
          <RouterLink :to="routeTo('settings')" class="menu-item" @click="onNavigate">
            <i class="icon pi pi-cog"></i>
            <span class="label">Einstellungen</span>
          </RouterLink>
        </li>
      </ul>
    </div>
  </nav>
</template>

<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import Select from 'primevue/select'

const props = defineProps({
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

const emit = defineEmits(['change-organisation', 'navigate'])

const organisationOptions = computed(() => props.organisations)

function routeTo(name) {
  const query = {}
  if (props.activeOrganisationId != null) {
    query.organisation = String(props.activeOrganisationId)
  }
  return { name, query }
}

function changeOrganisation(id) {
  emit('change-organisation', id)
}

function onNavigate() {
  emit('navigate')
}
</script>

<style scoped>
.nav-menu {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.organisation-context {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  padding: 0 1rem 0.25rem;
}

.organisation-context label {
  color: var(--p-text-muted-color);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.organisation-context :deep(.p-select) {
  width: 100%;
}

.nav-section {
  padding: 0 1rem;
}

.section-title {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--p-text-muted-color);
  margin: 0 1rem 0.75rem;
  text-transform: uppercase;
}

.menu-items {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.8rem 1rem;
  color: var(--p-text-color);
  text-decoration: none;
  border-radius: var(--p-border-radius-md);
  transition: background 0.2s ease, color 0.2s ease;
  cursor: pointer;
}

.menu-item:hover {
  background: var(--p-surface-hover);
}

.menu-item.router-link-active {
  background: var(--p-primary-50);
  color: var(--p-primary-color);
  font-weight: 600;
}

.icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.5rem;
  font-size: 1rem;
}

.label {
  flex: 1;
  font-size: 0.95rem;
}
</style>
