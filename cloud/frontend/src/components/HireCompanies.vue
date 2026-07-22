<template>
  <ListDetailLayout
    :title="$t('hireCompanies.title')"
    :subtitle="$t('hireCompanies.subtitle')"
    :createLabel="$t('hireCompanies.createLabel')"
    :showDetail="showDetail"
    @open-create="openCreateForm"
  >
    <template #header-actions>
      <HelpLink slug="roles-and-access" variant="icon" />
    </template>
    <template #detail>
      <h2>{{ editMode ? $t('hireCompanies.editTitle') : $t('hireCompanies.newTitle') }}</h2>
      <p class="form-required-legend"><span class="vq-asterisk">*</span> {{ $t('common.requiredLegend') }}</p>

      <v-form ref="formRef" @submit.prevent="saveCompany">
      <div class="form-field">
        <FormLabel required>{{ $t('common.name') }}</FormLabel>
        <v-text-field
          v-model="form.name"
          :placeholder="$t('hireCompanies.namePlaceholder')"
          hide-details="auto"
          required
          :rules="[rules.required]"
        />
      </div>
      <div class="form-field">
        <label>{{ $t('common.address') }}</label>
        <v-text-field v-model="form.address" :placeholder="$t('hireCompanies.addressPlaceholder')" hide-details="auto" />
      </div>
      <div class="field-row">
        <div class="form-field">
          <label>{{ $t('common.zip') }}</label>
          <v-text-field v-model="form.zip" :placeholder="$t('hireCompanies.zipPlaceholder')" hide-details="auto" />
        </div>
        <div class="form-field">
          <label>{{ $t('common.city') }}</label>
          <v-text-field v-model="form.city" :placeholder="$t('hireCompanies.cityPlaceholder')" hide-details="auto" />
        </div>
      </div>
      <div class="form-field">
        <label>{{ $t('common.country') }}</label>
        <v-select
          v-model="form.countryId"
          :items="countryOptions"
          item-title="title"
          item-value="value"
          :placeholder="$t('hireCompanies.countryPlaceholder')"
          hide-details="auto"
          clearable
        />
      </div>
      <ReceiptPrintingSection
        v-if="editMode && routeEntityId"
        :api-base-path="`/hire-companies/${routeEntityId}`"
        :entity-id="routeEntityId"
        :title="$t('hireCompanies.receiptTemplatesTitle')"
        :hint="$t('hireCompanies.receiptTemplatesHint')"
      />
      <div class="actions">
        <v-btn variant="outlined" type="button" @click="resetForm">{{ $t('common.back') }}</v-btn>
        <v-btn color="primary" type="submit">{{ $t('common.save') }}</v-btn>
      </div>
      <p v-if="message" :class="messageType">{{ message }}</p>
      </v-form>
    </template>

    <template #table>
      <div class="table-header">
        <h2>{{ $t('hireCompanies.allTitle') }}</h2>
        <span>{{ $t('common.entriesCountTotal', { total: companies.length }) }}</span>
      </div>
      <VqDataTable
        :headers="tableHeaders"
        :items="companies"
        item-value="id"
        hover
        hide-default-footer
        :no-data-text="$t('hireCompanies.noData')"
        class="vq-data-table list-table"
        @click:row="onCompanyRowClick"
      >
        <template #item.standort="{ item }">
          {{ item.address || $t('common.emDash') }}<span v-if="item.city"> · {{ item.city }}</span>
        </template>
        <template #item.country="{ item }">
          {{ item.country?.name || $t('common.emDash') }}
        </template>
        <template #item.actions="{ item }">
          <v-btn color="error" @click.stop="deleteCompany(item.id)">{{ $t('common.delete') }}</v-btn>
        </template>
      </VqDataTable>
    </template>
  </ListDetailLayout>
</template>

<script setup lang="ts">
import { inject, onMounted, ref, watch, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import FormLabel from './FormLabel.vue'
import ListDetailLayout from './ListDetailLayout.vue'
import HelpLink from './HelpLink.vue'
import ReceiptPrintingSection from './ReceiptPrintingSection.vue'
import { apiJson } from '../api'
import { useCountries } from '../composables/useCountries'
import { rules, validateForm } from '../utils/formRules.js'
import { useListDetailRouting } from '../composables/useListDetailRouting'
import { SESSION_CONTEXT_KEY } from '../sessionContext'
import VqDataTable from './VqDataTable.vue'

import type { HireCompanyRead } from '@/types/api'
import type { DataTableHeader } from '@/types/vuetify'

const { t } = useI18n()
const { countryOptions, fetchCountries } = useCountries()

const sessionContext = inject(SESSION_CONTEXT_KEY, null)

const route = useRoute()
const {
  isCreateMode,
  editMode,
  showDetail,
  routeEntityId,
  goToList,
  goToCreate,
  goToDetail,
} = useListDetailRouting('hire-companies')

const tableHeaders = computed((): DataTableHeader[] => [
  { title: t('common.id'), key: 'id' },
  { title: t('common.name'), key: 'name' },
  { title: t('common.location'), key: 'standort', sortable: false },
  { title: t('common.country'), key: 'country' },
  { title: t('common.actions'), key: 'actions', sortable: false, align: 'end' },
])

const companies = ref<HireCompanyRead[]>([])
const message = ref('')
const messageType = ref('')

const form = ref<{
  name: string
  address: string
  zip: string
  city: string
  countryId: number | null
}>({
  name: '',
  address: '',
  zip: '',
  city: '',
  countryId: null,
})

async function fetchCompanies() {
  try {
    companies.value = await apiJson<HireCompanyRead[]>('/hire-companies/')
  } catch {
    message.value = t('hireCompanies.loadError')
    messageType.value = 'error'
  }
}

const emptyForm = () => ({
  name: '',
  address: '',
  zip: '',
  city: '',
  countryId: null as number | null,
})

function applyCompanyToForm(row: HireCompanyRead) {
  form.value = {
    name: row.name || '',
    address: row.address || '',
    zip: row.zip || '',
    city: row.city || '',
    countryId: row.country_id ?? row.country?.id ?? null,
  }
  message.value = ''
}

function clearFormState() {
  form.value = emptyForm()
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
  let row = companies.value.find((c) => Number(c.id) === Number(id))
  if (!row) {
    try {
      row = await apiJson<HireCompanyRead>(`/hire-companies/${id}`)
    } catch {
      message.value = t('hireCompanies.notFound')
      messageType.value = 'error'
      goToList()
      return
    }
  }
  applyCompanyToForm(row)
}

watch(() => [route.name, route.params.id], syncRouteToForm, { immediate: true })

function resetForm() {
  goToList()
}

function openCreateForm() {
  goToCreate()
}

function onCompanyRowClick(_event: Event, { item }: { item: HireCompanyRead }) {
  editCompany(item)
}

function editCompany(row: HireCompanyRead) {
  applyCompanyToForm(row)
  goToDetail(row.id)
}

const formRef = ref(null)

async function saveCompany() {
  if (!(await validateForm(formRef))) return
  const payload = {
    name: form.value.name,
    address: form.value.address || null,
    zip: form.value.zip || null,
    city: form.value.city || null,
    country_id: form.value.countryId || null,
  }
  try {
    const path = editMode.value
      ? `/hire-companies/${routeEntityId.value}`
      : '/hire-companies/'
    const method = editMode.value ? 'PUT' : 'POST'
    const saved = await apiJson<HireCompanyRead>(path, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    const wasEdit = editMode.value
    await fetchCompanies()
    if (!wasEdit && sessionContext) {
      await sessionContext.reloadHireCompaniesAndSelect(saved.id)
    }
    message.value = wasEdit ? t('hireCompanies.updated') : t('hireCompanies.created')
    messageType.value = 'success'
    await goToList()
  } catch {
    message.value = t('hireCompanies.saveError')
    messageType.value = 'error'
  }
}

async function deleteCompany(id: number | string) {
  if (!confirm(t('hireCompanies.deleteConfirm'))) return
  try {
    await apiJson(`/hire-companies/${id}`, { method: 'DELETE' })
    await fetchCompanies()
    message.value = t('hireCompanies.deleted')
    messageType.value = 'success'
    if (Number(routeEntityId.value) === Number(id)) {
      await goToList()
    }
  } catch {
    message.value = t('hireCompanies.deleteError')
    messageType.value = 'error'
  }
}

onMounted(async () => {
  await fetchCountries()
  await fetchCompanies()
})
</script>

<style scoped>
h2 {
  margin: 0 0 1.5rem;
  color: rgb(var(--v-theme-on-surface));
}

label {
  color: rgb(var(--v-theme-on-surface));
  font-size: 0.875rem;
  font-weight: 600;
}

.table-header span {
  opacity: 0.7;
  font-size: 0.9rem;
}
</style>
