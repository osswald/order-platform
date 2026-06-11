<template>
  <ListDetailLayout
    :title="$t('organisations.title')"
    :subtitle="$t('organisations.subtitle')"
    :createLabel="$t('organisations.createLabel')"
    :showCreate="canAccessTenantAdmin"
    :showDetail="showDetail"
    @open-create="openCreateForm"
  >
    <template #detail>
      <h2>{{ editMode ? $t('organisations.editTitle') : $t('organisations.newTitle') }}</h2>
      <p class="form-required-legend"><span class="vq-asterisk">*</span> {{ $t('common.requiredLegend') }}</p>

      <template v-if="editMode && activeId">
        <p v-if="message" :class="messageType">{{ message }}</p>
        <SectionNavLayout
          :mobile="isMobile"
          v-model:active-tab="activeConfigTab"
          :sections="configSections"
          :nav-aria-label="$t('organisations.configNavAria')"
        >
          <template #stammdaten>
            <v-form ref="formRef" @submit.prevent="saveOrganisation">
              <OrganisationStammdatenFields
                :form="form"
                :country-options="countryOptions"
                :currency-options="currencyOptions"
              />
              <div class="actions">
                <v-btn variant="outlined" type="button" @click="resetForm">{{ $t('common.back') }}</v-btn>
                <v-btn color="primary" type="submit">{{ $t('common.save') }}</v-btn>
              </div>
            </v-form>
          </template>

          <template #geraete>
            <template v-if="orgApplianceLendings">
              <div class="org-lendings-toolbar">
                <v-btn color="primary" type="button" @click="lendingDialogVisible = true">
                  {{ $t('organisations.lendAppliances') }}
                </v-btn>
              </div>
              <div class="org-lendings-block">
                <h3>{{ $t('lending.currentTitle') }}</h3>
                <VqDataTable
                  :headers="lendingHeaders"
                  :items="orgApplianceLendings.current"
                  item-value="lending_id"
                  class="vq-data-table list-table nested-table"
                  hide-default-footer
                >
                  <template #item.appliance_name="{ item }">{{ item.appliance_name || $t('common.emDash') }}</template>
                  <template #item.appliance_type="{ item }">{{ applianceTypeLabel(item.appliance_type) }}</template>
                  <template #item.period="{ item }">
                    {{ formatDeDate(item.start_date) }} – {{ formatDeDate(item.end_date) }}
                  </template>
                  <template #no-data>{{ $t('lending.noCurrent') }}</template>
                </VqDataTable>
              </div>
              <div class="org-lendings-block">
                <h3>{{ $t('lending.plannedTitle') }}</h3>
                <VqDataTable
                  :headers="plannedLendingHeaders"
                  :items="orgApplianceLendings.planned"
                  item-value="lending_id"
                  class="vq-data-table list-table nested-table"
                  hide-default-footer
                >
                  <template #item.appliance_name="{ item }">{{ item.appliance_name || $t('common.emDash') }}</template>
                  <template #item.appliance_type="{ item }">{{ applianceTypeLabel(item.appliance_type) }}</template>
                  <template #item.period="{ item }">
                    {{ formatDeDate(item.start_date) }} – {{ formatDeDate(item.end_date) }}
                  </template>
                  <template #item.actions="{ item }">
                    <v-btn
                      variant="outlined"
                      size="small"
                      type="button"
                      :disabled="cancellingLendingId === item.lending_id"
                      @click="cancelPlannedLendingRow(item)"
                    >
                      {{ $t('common.cancelLending') }}
                    </v-btn>
                  </template>
                  <template #no-data>{{ $t('lending.noPlanned') }}</template>
                </VqDataTable>
              </div>
            </template>
          </template>

          <template #stripe>
            <OrganisationStripeSection :organisation-id="activeId" />
          </template>

          <template #belegvorlagen>
            <ReceiptPrintingSection
              :api-base-path="`/organisations/${activeId}`"
              :entity-id="activeId"
              :title="$t('organisations.receiptTemplatesOrgTitle')"
              :hint="$t('organisations.receiptTemplatesOrgHint')"
            />
          </template>

          <template #mwst>
            <p class="muted">{{ $t('organisations.config.taxComingSoon') }}</p>
          </template>
        </SectionNavLayout>

        <OrganisationLendingDialog
          v-model:visible="lendingDialogVisible"
          :organisation-id="activeId"
          :organisation-name="form.name"
          @completed="fetchOrgApplianceLendings(activeId)"
        />
      </template>

      <v-form v-else ref="formRef" @submit.prevent="saveOrganisation">
        <OrganisationStammdatenFields
          :form="form"
          :country-options="countryOptions"
          :currency-options="currencyOptions"
        />
        <div class="actions">
          <v-btn variant="outlined" type="button" @click="resetForm">{{ $t('common.back') }}</v-btn>
          <v-btn color="primary" type="submit">{{ $t('common.save') }}</v-btn>
        </div>
        <p v-if="message" :class="messageType">{{ message }}</p>
      </v-form>
    </template>

    <template #table>
      <ReceiptPrintingSection
        v-if="tenantHireCompanyId && canManageTenant"
        :api-base-path="`/hire-companies/${tenantHireCompanyId}`"
        :entity-id="tenantHireCompanyId"
        :title="$t('organisations.receiptTemplatesTenantTitle')"
        :hint="$t('organisations.receiptTemplatesTenantHint')"
      />
      <div class="table-header">
        <h2>{{ $t('organisations.allTitle') }}</h2>
        <span>{{ $t('common.entriesCount', { filtered: filteredOrganisations.length, total: organisations.length }) }}</span>
      </div>
      <div class="list-controls">
        <div class="search-field">
          <v-text-field
            v-model="searchQuery"
            :label="$t('common.search')"
            prepend-inner-icon="mdi-magnify"
            :placeholder="$t('organisations.searchPlaceholder')"
            hide-details
            density="compact"
          />
        </div>
        <div class="filter-field">
          <v-select
            v-model="countryFilter"
            :items="countryFilterOptions"
            item-title="label"
            item-value="value"
            :label="$t('common.country')"
            hide-details
            density="compact"
          />
        </div>
        <div class="filter-field">
          <v-select
            v-model="userFilter"
            :items="userFilterOptions"
            item-title="label"
            item-value="value"
            :label="$t('common.users')"
            hide-details
            density="compact"
          />
        </div>
      </div>
      <VqDataTable
        v-model:page="currentPage"
        :headers="tableHeaders"
        :items="filteredOrganisations"
        :items-per-page="pageSize"
        item-value="id"
        class="vq-data-table list-table"
        hover
        @click:row="(_, { item }) => editOrganisation(item)"
      >
        <template #item.location="{ item }">
          {{ item.address || $t('common.emDash') }}<span v-if="item.city"> · {{ item.city }}</span>
        </template>
        <template #item.user_ids="{ item }">{{ item.user_ids.length }}</template>
        <template v-if="canAccessTenantAdmin" #item.actions="{ item }">
          <v-btn color="error" variant="outlined" size="small" @click.stop="deleteOrganisation(item.id)">
            {{ $t('common.delete') }}
          </v-btn>
        </template>
        <template #no-data>{{ $t('organisations.noData') }}</template>
      </VqDataTable>
    </template>
  </ListDetailLayout>
</template>

<script setup>
import { ref, onMounted, computed, watch, inject } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import ListDetailLayout from './ListDetailLayout.vue'
import OrganisationLendingDialog from './OrganisationLendingDialog.vue'
import OrganisationStammdatenFields from './OrganisationStammdatenFields.vue'
import OrganisationStripeSection from './OrganisationStripeSection.vue'
import ReceiptPrintingSection from './ReceiptPrintingSection.vue'
import SectionNavLayout from './SectionNavLayout.vue'
import { apiFetch } from '../api'
import { validateForm } from '../utils/formRules.js'
import {
  cancelPlannedLending,
  applianceTypeLabel,
  formatDeDate,
} from '../utils/applianceLending'
import { useListDetailRouting } from '../composables/useListDetailRouting'
import { useClientPagination } from '../composables/useClientPagination'
import { useBreakpoint } from '../composables/useBreakpoint'
import { SESSION_CONTEXT_KEY } from '../sessionContext'
import VqDataTable from './VqDataTable.vue'

const props = defineProps({
  canAccessTenantAdmin: { type: Boolean, default: false },
})

const { t } = useI18n()

const sessionContext = inject(SESSION_CONTEXT_KEY, null)
const tenantHireCompanyId = computed(() => sessionContext?.activeHireCompanyId?.value ?? null)
const canManageTenant = computed(() => props.canAccessTenantAdmin)

const route = useRoute()
const {
  isCreateMode,
  editMode,
  showDetail,
  routeEntityId,
  goToList,
  goToCreate,
  goToDetail,
} = useListDetailRouting('organisations')

const organisations = ref([])
const activeId = computed(() => routeEntityId.value)
const message = ref('')
const messageType = ref('')
const searchQuery = ref('')
const countryFilter = ref('')
const userFilter = ref('')
const orgApplianceLendings = ref(null)
const lendingDialogVisible = ref(false)
const cancellingLendingId = ref(null)
const countryOptions = ['Deutschland', 'Österreich', 'Schweiz', 'Frankreich', 'Italien', 'Belgien', 'Niederlande']
const currencyOptions = ['EUR', 'CHF', 'USD', 'GBP']

const { matches: isMobile } = useBreakpoint(768)
const activeConfigTab = ref('stammdaten')

const configSections = computed(() => {
  if (!editMode.value || !activeId.value) return []
  return [
    { id: 'stammdaten', title: t('organisations.config.sectionStammdaten'), defaultOpen: true },
    { id: 'geraete', title: t('organisations.config.sectionGeraete') },
    { id: 'stripe', title: t('organisations.config.sectionStripe') },
    { id: 'belegvorlagen', title: t('organisations.config.sectionBelegvorlagen') },
    { id: 'mwst', title: t('organisations.config.sectionMwst') },
  ]
})

watch(
  configSections,
  (sections) => {
    if (!sections.some((s) => s.id === activeConfigTab.value)) {
      activeConfigTab.value = sections[0]?.id ?? 'stammdaten'
    }
  },
  { immediate: true },
)

const userFilterOptions = computed(() => [
  { value: '', label: t('common.all') },
  { value: 'with-users', label: t('organisations.withUsers') },
  { value: 'without-users', label: t('organisations.withoutUsers') },
])

const tableHeaders = computed(() => [
  { title: t('common.id'), key: 'id' },
  { title: t('common.name'), key: 'name' },
  { title: t('common.location'), key: 'location', sortable: false },
  { title: t('common.country'), key: 'country' },
  { title: t('organisations.currency'), key: 'currency' },
  { title: t('common.users'), key: 'user_ids', sortable: false },
  { title: t('common.actions'), key: 'actions', sortable: false, align: 'end' },
])

const lendingHeaders = computed(() => [
  { title: t('common.id'), key: 'appliance_id' },
  { title: t('common.appliance'), key: 'appliance_name', sortable: false },
  { title: t('common.type'), key: 'appliance_type', sortable: false },
  { title: t('common.period'), key: 'period', sortable: false },
])

const plannedLendingHeaders = computed(() => [
  ...lendingHeaders.value,
  { title: t('common.action'), key: 'actions', sortable: false, align: 'end' },
])

const form = ref({
  name: '',
  address: '',
  zip: '',
  city: '',
  country: '',
  currency: 'EUR',
  userIdsArray: [],
})

function matchesSearch(org, term) {
  if (!term) return true
  return [
    org.id,
    org.name,
    org.address,
    org.zip,
    org.city,
    org.country,
    org.currency,
  ]
    .filter((value) => value !== null && value !== undefined)
    .some((value) => String(value).toLowerCase().includes(term))
}

const availableCountries = computed(() => {
  return [...new Set(organisations.value.map((org) => org.country).filter(Boolean))].sort()
})

const countryFilterOptions = computed(() => [
  { value: '', label: t('common.allCountries') },
  ...availableCountries.value.map((country) => ({ value: country, label: country })),
])

const filteredOrganisations = computed(() => {
  const term = searchQuery.value.trim().toLowerCase()
  return organisations.value.filter((org) => {
    if (!matchesSearch(org, term)) return false
    if (countryFilter.value && org.country !== countryFilter.value) return false
    const userCount = Array.isArray(org.user_ids) ? org.user_ids.length : 0
    if (userFilter.value === 'with-users' && userCount === 0) return false
    if (userFilter.value === 'without-users' && userCount > 0) return false
    return true
  })
})

const { currentPage, pageSize } = useClientPagination(filteredOrganisations, {
  resetOn: [searchQuery, countryFilter, userFilter],
})

function parseUserIds(value) {
  return value
    .split(',')
    .map((id) => id.trim())
    .filter(Boolean)
    .map(Number)
    .filter((id) => !Number.isNaN(id))
}

async function fetchOrganisations() {
  try {
    const response = await apiFetch('/organisations/')
    organisations.value = await response.json()
  } catch (error) {
    message.value = t('organisations.loadError')
    messageType.value = 'error'
  }
}

async function fetchOrgApplianceLendings(orgId) {
  orgApplianceLendings.value = null
  try {
    const response = await apiFetch(`/organisations/${orgId}/appliance-lendings`)
    if (!response.ok) throw new Error(await response.text())
    orgApplianceLendings.value = await response.json()
  } catch {
    orgApplianceLendings.value = { current: [], planned: [], past: [] }
  }
}

async function cancelPlannedLendingRow(row) {
  if (!activeId.value || !row?.lending_id) return
  const label = row.appliance_name || t('lending.deviceFallback', { id: row.appliance_id })
  if (!confirm(t('lending.cancelConfirm', { label }))) return
  cancellingLendingId.value = row.lending_id
  message.value = ''
  try {
    await cancelPlannedLending(activeId.value, row.lending_id)
    message.value = t('lending.cancelSuccess')
    messageType.value = 'success'
    await fetchOrgApplianceLendings(activeId.value)
  } catch (e) {
    message.value = e.message || t('lending.cancelFailed')
    messageType.value = 'error'
  } finally {
    cancellingLendingId.value = null
  }
}

const emptyOrgForm = () => ({
  name: '',
  address: '',
  zip: '',
  city: '',
  country: '',
  currency: 'EUR',
  userIdsArray: [],
})

function applyOrganisationToForm(org) {
  form.value = {
    name: org.name,
    address: org.address || '',
    zip: org.zip || '',
    city: org.city || '',
    country: org.country,
    currency: org.currency || 'EUR',
    userIdsArray: org.user_ids ? org.user_ids.slice() : [],
  }
  message.value = ''
}

function clearFormState() {
  orgApplianceLendings.value = null
  lendingDialogVisible.value = false
  activeConfigTab.value = 'stammdaten'
  form.value = emptyOrgForm()
  message.value = ''
}

async function syncRouteToForm() {
  if (!showDetail.value) {
    clearFormState()
    return
  }
  if (isCreateMode.value) {
    clearFormState()
    return
  }
  const id = routeEntityId.value
  if (id == null) {
    goToList()
    return
  }
  let row = organisations.value.find((o) => Number(o.id) === Number(id))
  if (!row) {
    try {
      const response = await apiFetch(`/organisations/${id}`)
      if (!response.ok) throw new Error(await response.text())
      row = await response.json()
    } catch {
      message.value = t('organisations.notFound')
      messageType.value = 'error'
      goToList()
      return
    }
  }
  applyOrganisationToForm(row)
  fetchOrgApplianceLendings(id)
}

watch(() => [route.name, route.params.id], syncRouteToForm, { immediate: true })

function resetForm() {
  goToList()
}

function openCreateForm() {
  goToCreate()
}

function editOrganisation(org) {
  applyOrganisationToForm(org)
  goToDetail(org.id)
  fetchOrgApplianceLendings(org.id)
}

const formRef = ref(null)

async function saveOrganisation() {
  if (!(await validateForm(formRef))) return
  const payload = {
    name: form.value.name,
    address: form.value.address || null,
    zip: form.value.zip || null,
    city: form.value.city || null,
    country: form.value.country,
    currency: form.value.currency,
    user_ids: Array.isArray(form.value.userIdsArray) ? form.value.userIdsArray : parseUserIds(form.value.userIds || ''),
  }

  try {
    const path = editMode.value ? `/organisations/${activeId.value}` : '/organisations/'
    const method = editMode.value ? 'PUT' : 'POST'
    const response = await apiFetch(path, {
      method,
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })
    if (!response.ok) {
      throw new Error(await response.text())
    }
    const saved = await response.json()
    const wasEdit = editMode.value
    await fetchOrganisations()
    if (!wasEdit && sessionContext) {
      await sessionContext.reloadOrganisationsAndSelect(saved.id)
    }
    message.value = wasEdit ? t('organisations.updated') : t('organisations.created')
    messageType.value = 'success'
    await goToList()
  } catch {
    message.value = t('organisations.saveError')
    messageType.value = 'error'
  }
}

async function deleteOrganisation(id) {
  if (!confirm(t('organisations.deleteConfirm'))) {
    return
  }
  try {
    const response = await apiFetch(`/organisations/${id}`, {
      method: 'DELETE',
    })
    if (!response.ok) {
      throw new Error(await response.text())
    }
    await fetchOrganisations()
    message.value = t('organisations.deleted')
    messageType.value = 'success'
    if (Number(routeEntityId.value) === Number(id)) {
      await goToList()
    }
  } catch {
    message.value = t('organisations.deleteError')
    messageType.value = 'error'
  }
}

onMounted(fetchOrganisations)
</script>

<style scoped>
h2 {
  margin: 0 0 1.5rem;
  color: rgb(var(--v-theme-on-surface));
}

.muted {
  color: rgba(var(--v-theme-on-surface), 0.65);
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 1.25rem;
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
}

.table-header h2 {
  margin: 0;
}

.table-header span {
  color: rgba(var(--v-theme-on-surface), 0.65);
  font-size: 0.9rem;
}

.list-controls {
  display: grid;
  grid-template-columns: minmax(240px, 1fr) 180px 180px;
  gap: 1rem;
  margin-bottom: 1rem;
}

.search-field,
.filter-field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.list-table {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  overflow: hidden;
}

.org-lendings-toolbar {
  margin-top: 0;
}

.org-lendings-block {
  margin-top: 1rem;
}

.org-lendings-block h3 {
  margin: 0 0 0.75rem;
  font-size: 1rem;
  color: rgb(var(--v-theme-on-surface));
}

.nested-table {
  margin-bottom: 0.5rem;
}

@media (max-width: 1000px) {
  .list-controls {
    grid-template-columns: 1fr;
  }
}
</style>
