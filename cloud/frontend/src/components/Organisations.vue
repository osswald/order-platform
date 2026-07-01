<template>
  <ListDetailLayout
    :title="$t('organisations.title')"
    :subtitle="$t('organisations.subtitle')"
    :createLabel="$t('organisations.createLabel')"
    :showCreate="canAccessTenantAdmin"
    :showDetail="showDetail"
    @open-create="openCreateForm"
  >
    <template #header-actions>
      <HelpLink slug="organisation-setup" variant="icon" />
    </template>
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
                v-model:form="form"
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
                  <template #item.appliance_type="{ item }">
                    <ApplianceTypeChip :type="item.appliance_type" />
                  </template>
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
                  <template #item.appliance_type="{ item }">
                    <ApplianceTypeChip :type="item.appliance_type" />
                  </template>
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

          <template #farbpalette>
            <OrganisationColorPaletteSection :organisation-id="activeId" />
          </template>

          <template #buchhaltung>
            <OrganisationAccountingSection
              :organisation-id="activeId"
              :country-id="form.countryId ?? undefined"
            />
          </template>

          <template #positionen>
            <OrganisationPositionCommentsSection :organisation-id="activeId" />
          </template>

          <template #zutaten>
            <OrganisationIngredientsSection :organisation-id="activeId" />
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
          v-model:form="form"
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
        <template #item.country="{ item }">
          {{ item.country?.name || $t('common.emDash') }}
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

<script setup lang="ts">
import { ref, onMounted, computed, watch, inject } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import ListDetailLayout from './ListDetailLayout.vue'
import OrganisationLendingDialog from './OrganisationLendingDialog.vue'
import ApplianceTypeChip from './ApplianceTypeChip.vue'
import OrganisationStammdatenFields from './OrganisationStammdatenFields.vue'
import OrganisationStripeSection from './OrganisationStripeSection.vue'
import ReceiptPrintingSection from './ReceiptPrintingSection.vue'
import OrganisationAccountingSection from './OrganisationAccountingSection.vue'
import OrganisationPositionCommentsSection from './OrganisationPositionCommentsSection.vue'
import OrganisationIngredientsSection from './OrganisationIngredientsSection.vue'
import OrganisationColorPaletteSection from './OrganisationColorPaletteSection.vue'
import SectionNavLayout from './SectionNavLayout.vue'
import { apiJson } from '../api'
import { useCountries } from '../composables/useCountries'
import { validateForm } from '../utils/formRules.js'
import {
  cancelPlannedLending,
  formatDeDate,
} from '../utils/applianceLending'
import { useListDetailRouting } from '../composables/useListDetailRouting'
import { useClientPagination } from '../composables/useClientPagination'
import { useBreakpoint } from '../composables/useBreakpoint'
import { MOBILE_BREAKPOINT } from '../constants/layout'
import { SESSION_CONTEXT_KEY } from '../sessionContext'
import VqDataTable from './VqDataTable.vue'
import HelpLink from './HelpLink.vue'
import type {
  OrganisationApplianceLendingsRead,
  OrganisationRead,
  OrgApplianceLendingItem,
} from '@/types/api'
import { getErrorMessage } from '@/types/api'
import type { OrganisationStammdatenForm, SectionNavSection } from '@/types/ui'
import type { DataTableHeader } from '@/types/vuetify'
import type { SessionContext } from '@/types/ui'

const props = defineProps<{
  canAccessTenantAdmin?: boolean
}>()

const { t } = useI18n()

const sessionContext = inject<SessionContext | null>(SESSION_CONTEXT_KEY, null)
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

const organisations = ref<OrganisationRead[]>([])
const activeId = computed(() => routeEntityId.value)
const message = ref('')
const messageType = ref('')
const searchQuery = ref('')
const countryFilter = ref('')
const userFilter = ref('')
const orgApplianceLendings = ref<OrganisationApplianceLendingsRead | null>(null)
const lendingDialogVisible = ref(false)
const cancellingLendingId = ref<number | null>(null)
const { countryOptions, fetchCountries } = useCountries()
const currencyOptions = ['EUR', 'CHF', 'USD', 'GBP']

const { matches: isMobile } = useBreakpoint(MOBILE_BREAKPOINT)
const activeConfigTab = ref('stammdaten')

const configSections = computed((): SectionNavSection[] => {
  if (!editMode.value || !activeId.value) return []
  return [
    { id: 'stammdaten', title: t('organisations.config.sectionStammdaten'), defaultOpen: true },
    { id: 'geraete', title: t('organisations.config.sectionGeraete') },
    { id: 'stripe', title: t('organisations.config.sectionStripe') },
    { id: 'belegvorlagen', title: t('organisations.config.sectionBelegvorlagen') },
    { id: 'farbpalette', title: t('organisations.config.sectionColorPalette') },
    { id: 'positionen', title: t('organisations.config.sectionPositionen') },
    { id: 'zutaten', title: t('organisations.config.sectionZutaten') },
    { id: 'buchhaltung', title: t('organisations.config.sectionBuchhaltung') },
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

function applySectionFromQuery() {
  const section = typeof route.query.section === 'string' ? route.query.section : ''
  if (!section || !editMode.value) return
  if (configSections.value.some((sectionItem) => sectionItem.id === section)) {
    activeConfigTab.value = section
  }
}

watch(
  () => [route.query.section, editMode.value, activeId.value],
  applySectionFromQuery,
  { immediate: true },
)

const userFilterOptions = computed(() => [
  { value: '', label: t('common.all') },
  { value: 'with-users', label: t('organisations.withUsers') },
  { value: 'without-users', label: t('organisations.withoutUsers') },
])

const tableHeaders = computed((): DataTableHeader[] => [
  { title: t('common.id'), key: 'id' },
  { title: t('common.name'), key: 'name' },
  { title: t('common.location'), key: 'location', sortable: false },
  { title: t('common.country'), key: 'country' },
  { title: t('organisations.currency'), key: 'currency' },
  { title: t('common.users'), key: 'user_ids', sortable: false },
  { title: t('common.actions'), key: 'actions', sortable: false, align: 'end' },
])

const lendingHeaders = computed((): DataTableHeader[] => [
  { title: t('common.id'), key: 'appliance_id' },
  { title: t('common.appliance'), key: 'appliance_name', sortable: false },
  { title: t('common.type'), key: 'appliance_type', sortable: false },
  { title: t('common.period'), key: 'period', sortable: false },
])

const plannedLendingHeaders = computed((): DataTableHeader[] => [
  ...lendingHeaders.value,
  { title: t('common.action'), key: 'actions', sortable: false, align: 'end' },
])

const form = ref<OrganisationStammdatenForm>({
  name: '',
  address: '',
  zip: '',
  city: '',
  countryId: null,
  currency: 'EUR',
  userIdsArray: [],
})

function matchesSearch(org: OrganisationRead, term: string): boolean {
  if (!term) return true
  return [
    org.id,
    org.name,
    org.address,
    org.zip,
    org.city,
    org.country?.name,
    org.currency,
  ]
    .filter((value) => value !== null && value !== undefined)
    .some((value) => String(value).toLowerCase().includes(term))
}

const availableCountries = computed(() => {
  return [...new Set(organisations.value.map((org) => org.country?.name).filter(Boolean))].sort()
})

const countryFilterOptions = computed(() => [
  { value: '', label: t('common.allCountries') },
  ...availableCountries.value.map((country) => ({ value: country, label: country })),
])

const filteredOrganisations = computed(() => {
  const term = searchQuery.value.trim().toLowerCase()
  return organisations.value.filter((org) => {
    if (!matchesSearch(org, term)) return false
    if (countryFilter.value && org.country?.name !== countryFilter.value) return false
    const userCount = Array.isArray(org.user_ids) ? org.user_ids.length : 0
    if (userFilter.value === 'with-users' && userCount === 0) return false
    if (userFilter.value === 'without-users' && userCount > 0) return false
    return true
  })
})

const { currentPage, pageSize } = useClientPagination(filteredOrganisations, {
  resetOn: [searchQuery, countryFilter, userFilter],
})

async function fetchOrganisations() {
  try {
    organisations.value = await apiJson<OrganisationRead[]>('/organisations/')
  } catch {
    message.value = t('organisations.loadError')
    messageType.value = 'error'
  }
}

async function fetchOrgApplianceLendings(orgId: number) {
  orgApplianceLendings.value = null
  try {
    orgApplianceLendings.value = await apiJson<OrganisationApplianceLendingsRead>(
      `/organisations/${orgId}/appliance-lendings`,
    )
  } catch {
    orgApplianceLendings.value = { current: [], planned: [], past: [] }
  }
}

async function cancelPlannedLendingRow(row: OrgApplianceLendingItem) {
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
  } catch (e: unknown) {
    message.value = getErrorMessage(e, t('lending.cancelFailed'))
    messageType.value = 'error'
  } finally {
    cancellingLendingId.value = null
  }
}

const emptyOrgForm = (): OrganisationStammdatenForm => ({
  name: '',
  address: '',
  zip: '',
  city: '',
  countryId: null,
  currency: 'EUR',
  userIdsArray: [],
})

function applyOrganisationToForm(org: OrganisationRead) {
  form.value = {
    name: org.name,
    address: org.address || '',
    zip: org.zip || '',
    city: org.city || '',
    countryId: org.country_id ?? org.country?.id ?? null,
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
      row = await apiJson<OrganisationRead>(`/organisations/${id}`)
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

function editOrganisation(org: OrganisationRead) {
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
    country_id: form.value.countryId,
    currency: form.value.currency,
    user_ids: form.value.userIdsArray,
  }

  try {
    const path = editMode.value ? `/organisations/${activeId.value}` : '/organisations/'
    const method = editMode.value ? 'PUT' : 'POST'
    const saved = await apiJson<OrganisationRead>(path, {
      method,
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })
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

async function deleteOrganisation(id: number) {
  if (!confirm(t('organisations.deleteConfirm'))) {
    return
  }
  try {
    await apiJson(`/organisations/${id}`, {
      method: 'DELETE',
    })
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

onMounted(async () => {
  await fetchCountries()
  await fetchOrganisations()
})
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
