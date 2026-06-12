<template>
  <nav class="nav-menu">
    <div v-if="showHireCompanyPicker" class="organisation-context">
      <label>{{ $t('nav.activeHireCompany') }}</label>
      <v-select
        v-if="hireCompanyOptions.length > 1"
        :model-value="activeHireCompanyId"
        :items="hireCompanyOptions"
        item-title="name"
        item-value="id"
        :label="$t('nav.selectHireCompany')"
        density="compact"
        hide-details
        @update:model-value="changeHireCompany"
      />
      <span v-else-if="hireCompanyOptions.length === 1" class="context-value">
        {{ activeHireCompanyName }}
      </span>
      <span v-else class="context-value context-value--muted">{{ $t('nav.noHireCompanies') }}</span>
    </div>

    <div class="organisation-context">
      <label>{{ $t('nav.activeOrganisation') }}</label>
      <v-select
        v-if="organisationOptions.length > 1"
        :model-value="activeOrganisationId"
        :items="organisationOptions"
        item-title="name"
        item-value="id"
        :label="$t('common.noOrganisationShort')"
        density="compact"
        hide-details
        @update:model-value="changeOrganisation"
      />
      <span v-else-if="organisationOptions.length === 1" class="context-value">
        {{ activeOrganisationName }}
      </span>
      <span v-else class="context-value context-value--muted">{{ $t('common.noOrganisationShort') }}</span>
    </div>

    <div class="nav-section">
      <h3 class="section-title">{{ $t('nav.mainMenu') }}</h3>
      <v-list density="compact" nav>
        <v-list-item
          :to="routeTo('dashboard')"
          prepend-icon="mdi-chart-line"
          :title="$t('nav.dashboard')"
          @click="onNavigate"
        />
        <v-list-item
          :to="routeTo('events')"
          prepend-icon="mdi-calendar"
          :title="$t('nav.events')"
          @click="onNavigate"
        />
        <v-list-item
          :to="routeTo('waiters')"
          prepend-icon="mdi-card-account-details"
          :title="$t('nav.waiters')"
          @click="onNavigate"
        />
        <v-list-item
          :to="routeTo('articles')"
          prepend-icon="mdi-tag-multiple"
          :title="$t('nav.articles')"
          @click="onNavigate"
        />
        <v-list-item
          :to="routeTo('article-categories')"
          prepend-icon="mdi-folder"
          :title="$t('nav.articleCategories')"
          @click="onNavigate"
        />
        <v-list-item
          :to="routeTo('appliance-lendings')"
          prepend-icon="mdi-calendar-plus"
          :title="$t('nav.applianceLendings')"
          @click="onNavigate"
        />
      </v-list>
    </div>

    <div class="nav-section">
      <h3 class="section-title">{{ $t('nav.administration') }}</h3>
      <v-list density="compact" nav>
        <v-list-item
          v-if="isPlatformAdmin"
          :to="{ name: 'hire-companies' }"
          prepend-icon="mdi-briefcase"
          :title="$t('nav.hireCompanies')"
          @click="onNavigate"
        />
        <v-list-item
          v-if="isTenantAdminRole"
          :to="{ name: 'tenant-settings' }"
          prepend-icon="mdi-briefcase-edit"
          :title="$t('nav.tenantSettings')"
          @click="onNavigate"
        />
        <v-list-item
          v-if="canAccessOrganisationSettings"
          :to="routeTo('organisations')"
          prepend-icon="mdi-office-building"
          :title="$t('nav.organisations')"
          @click="onNavigate"
        />
        <v-list-item
          v-if="canAccessTenantAdmin"
          :to="routeTo('appliances')"
          prepend-icon="mdi-monitor"
          :title="$t('nav.appliances')"
          @click="onNavigate"
        />
        <v-list-item
          :to="{ name: 'countries' }"
          prepend-icon="mdi-earth"
          :title="$t('nav.countries')"
          @click="onNavigate"
        />
        <v-list-item
          :to="{ name: 'tax-codes' }"
          prepend-icon="mdi-percent"
          :title="$t('nav.taxCodes')"
          @click="onNavigate"
        />
        <v-list-item
          v-if="canAccessUsers"
          :to="routeTo('users')"
          prepend-icon="mdi-account"
          :title="$t('nav.users')"
          @click="onNavigate"
        />
        <v-list-item
          :to="routeTo('settings')"
          prepend-icon="mdi-cog"
          :title="$t('nav.settings')"
          @click="onNavigate"
        />
      </v-list>
    </div>

    <div class="nav-section">
      <h3 class="section-title">{{ $t('nav.helpSection') }}</h3>
      <v-list density="compact" nav>
        <v-list-item
          :to="{ name: 'help' }"
          prepend-icon="mdi-help-circle-outline"
          :title="$t('nav.help')"
          @click="onNavigate"
        />
      </v-list>
    </div>
  </nav>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps({
  isPlatformAdmin: {
    type: Boolean,
    default: false,
  },
  canAccessTenantAdmin: {
    type: Boolean,
    default: false,
  },
  canAccessOrganisationSettings: {
    type: Boolean,
    default: false,
  },
  canAccessUsers: {
    type: Boolean,
    default: false,
  },
  isTenantAdminRole: {
    type: Boolean,
    default: false,
  },
  hireCompanies: {
    type: Array,
    default: () => [],
  },
  activeHireCompanyId: {
    type: Number,
    default: null,
  },
  showHireCompanyPicker: {
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

const emit = defineEmits(['change-organisation', 'change-hire-company', 'navigate'])

const organisationOptions = computed(() => props.organisations)
const hireCompanyOptions = computed(() => props.hireCompanies)

const activeHireCompanyName = computed(() => {
  const company = hireCompanyOptions.value.find(
    (c) => Number(c.id) === Number(props.activeHireCompanyId),
  )
  return company?.name ?? hireCompanyOptions.value[0]?.name ?? t('common.emDash')
})

const activeOrganisationName = computed(() => {
  const org = organisationOptions.value.find(
    (o) => Number(o.id) === Number(props.activeOrganisationId),
  )
  return org?.name ?? organisationOptions.value[0]?.name ?? t('common.emDash')
})

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

function changeHireCompany(id) {
  emit('change-hire-company', id)
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
  padding-inline: 0.25rem;
}

.organisation-context {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.organisation-context label {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  opacity: 0.65;
  text-transform: uppercase;
}

.context-value {
  font-size: 0.95rem;
  font-weight: 600;
  padding: 0.15rem 0;
}

.context-value--muted {
  font-weight: 500;
  opacity: 0.65;
}

.section-title {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  opacity: 0.65;
  margin: 0 0 0.5rem;
  text-transform: uppercase;
}
</style>
