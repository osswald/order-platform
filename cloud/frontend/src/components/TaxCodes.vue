<template>
  <ListDetailLayout
    :title="$t('taxCodes.title')"
    :subtitle="$t('taxCodes.subtitle')"
    :createLabel="$t('taxCodes.createLabel')"
    :showCreate="isAdmin"
    :showDetail="showDetail"
    @open-create="openCreateForm"
  >
    <template #detail>
      <h2>{{ editMode ? $t('taxCodes.editTitle') : $t('taxCodes.newTitle') }}</h2>
      <p class="form-required-legend"><span class="vq-asterisk">*</span> {{ $t('common.requiredLegend') }}</p>

      <v-form ref="formRef" @submit.prevent="saveTaxCode">
        <div class="form-field">
          <FormLabel required>{{ $t('common.name') }}</FormLabel>
          <v-text-field
            v-model="form.name"
            :placeholder="$t('taxCodes.namePlaceholder')"
            hide-details="auto"
            :readonly="!isAdmin"
            required
            :rules="[rules.required]"
          />
        </div>
        <div class="form-field">
          <FormLabel required>{{ $t('common.country') }}</FormLabel>
          <v-select
            v-model="form.countryId"
            :items="countryOptions"
            item-title="title"
            item-value="value"
            :placeholder="$t('taxCodes.selectCountry')"
            hide-details="auto"
            :readonly="!isAdmin"
            required
            :rules="[rules.required]"
          />
        </div>

        <div class="rates-block">
          <div class="rates-header">
            <h3>{{ $t('taxCodes.ratesTitle') }}</h3>
            <v-btn v-if="isAdmin" variant="outlined" size="small" type="button" @click="addRateRow">
              {{ $t('taxCodes.addRate') }}
            </v-btn>
          </div>
          <p class="muted">{{ $t('taxCodes.ratesHint') }}</p>
          <div v-for="(rate, index) in form.rates" :key="index" class="rate-row">
            <v-text-field
              v-model.number="rate.ratePercent"
              type="number"
              step="0.1"
              min="0"
              :label="$t('taxCodes.ratePercent')"
              hide-details="auto"
              :readonly="!isAdmin"
              required
            />
            <v-text-field
              v-model="rate.validFrom"
              type="date"
              :label="$t('taxCodes.validFrom')"
              hide-details="auto"
              :readonly="!isAdmin"
              required
            />
            <v-text-field
              v-model="rate.validTo"
              type="date"
              :label="$t('taxCodes.validTo')"
              :placeholder="$t('common.optional')"
              hide-details="auto"
              :readonly="!isAdmin"
            />
            <v-btn
              v-if="isAdmin && form.rates.length > 1"
              icon="mdi-close"
              variant="text"
              type="button"
              @click="removeRateRow(index)"
            />
          </div>
        </div>

        <div v-if="isAdmin" class="actions">
          <v-btn variant="outlined" type="button" @click="resetForm">{{ $t('common.back') }}</v-btn>
          <v-btn v-if="editMode" color="error" variant="outlined" type="button" @click="deleteTaxCode">
            {{ $t('common.delete') }}
          </v-btn>
          <v-btn color="primary" type="submit">{{ $t('common.save') }}</v-btn>
        </div>
        <div v-else class="actions">
          <v-btn variant="outlined" type="button" @click="resetForm">{{ $t('common.back') }}</v-btn>
        </div>
        <p v-if="message" :class="messageType">{{ message }}</p>
      </v-form>
    </template>

    <template #table>
      <div class="table-header">
        <h2>{{ $t('taxCodes.allTitle') }}</h2>
        <span>{{ $t('common.entriesCountTotal', { total: filteredTaxCodes.length }) }}</span>
      </div>
      <div class="list-controls">
        <div class="filter-field">
          <v-select
            v-model="countryFilter"
            :items="countryFilterOptions"
            item-title="label"
            item-value="value"
            :label="$t('common.country')"
            hide-details
            density="compact"
            clearable
          />
        </div>
      </div>
      <VqDataTable
        :headers="tableHeaders"
        :items="filteredTaxCodes"
        item-value="id"
        hover
        hide-default-footer
        :no-data-text="$t('taxCodes.noData')"
        class="vq-data-table list-table"
        @click:row="onTaxCodeRowClick"
      >
        <template #item.country="{ item }">
          {{ item.country?.name || $t('common.emDash') }}
        </template>
        <template #item.currentRate="{ item }">
          {{ formatCurrentRate(item) }}
        </template>
        <template v-if="isAdmin" #item.actions="{ item }">
          <v-btn color="error" variant="text" @click.stop="deleteTaxCodeRow(item.id)">
            {{ $t('common.delete') }}
          </v-btn>
        </template>
      </VqDataTable>
    </template>
  </ListDetailLayout>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import FormLabel from './FormLabel.vue'
import ListDetailLayout from './ListDetailLayout.vue'
import VqDataTable from './VqDataTable.vue'
import { apiJson } from '../api'
import { rules, validateForm, type ValidatableForm } from '../utils/formRules.js'
import { useCountries } from '../composables/useCountries'
import { useListDetailRouting } from '../composables/useListDetailRouting'
import type { TaxCodeRead, TaxCodeRateRead } from '@/types/api'
import { getErrorMessage } from '@/types/api'
import type { TaxCodeForm } from '@/types/ui'
import type { DataTableHeader } from '@/types/vuetify'

const props = defineProps<{
  isAdmin?: boolean
}>()

const { t } = useI18n()
const route = useRoute()
const { countryOptions, fetchCountries } = useCountries()
const {
  isCreateMode,
  editMode,
  showDetail,
  routeEntityId,
  goToList,
  goToCreate,
  goToDetail,
} = useListDetailRouting('tax-codes')

const taxCodes = ref<TaxCodeRead[]>([])
const countryFilter = ref<number | null>(null)
const message = ref('')
const messageType = ref('')
const formRef = ref<ValidatableForm | null>(null)

const emptyRate = () => ({
  ratePercent: null as number | null,
  validFrom: '',
  validTo: '',
})

const form = ref<TaxCodeForm>({
  name: '',
  countryId: null,
  rates: [emptyRate()],
})

const tableHeaders = computed((): DataTableHeader[] => {
  const headers: DataTableHeader[] = [
    { title: t('common.id'), key: 'id' },
    { title: t('common.country'), key: 'country', sortable: false },
    { title: t('common.name'), key: 'name' },
    { title: t('taxCodes.currentRate'), key: 'currentRate', sortable: false },
  ]
  if (props.isAdmin) {
    headers.push({ title: t('common.actions'), key: 'actions', sortable: false, align: 'end' })
  }
  return headers
})

const countryFilterOptions = computed(() => [
  { value: null, label: t('common.allCountries') },
  ...countryOptions.value.map((option) => ({ value: option.value, label: option.title })),
])

const filteredTaxCodes = computed(() => {
  if (countryFilter.value == null) return taxCodes.value
  return taxCodes.value.filter((row) => Number(row.country_id) === Number(countryFilter.value))
})

function formatCurrentRate(item: TaxCodeRead): string {
  const rates = Array.isArray(item.rates) ? item.rates : []
  if (!rates.length) return t('common.emDash')
  const open = rates.filter((rate: TaxCodeRateRead) => !rate.valid_to)
  const chosen = (open.length ? open : rates)
    .slice()
    .sort((a: TaxCodeRateRead, b: TaxCodeRateRead) =>
      String(b.valid_from).localeCompare(String(a.valid_from)),
    )[0]
  if (!chosen) return t('common.emDash')
  return `${chosen.rate_percent}%`
}

function mapRatesToForm(rates: TaxCodeRateRead[] | null | undefined) {
  if (!Array.isArray(rates) || !rates.length) return [emptyRate()]
  return rates.map((rate) => ({
    ratePercent: rate.rate_percent,
    validFrom: rate.valid_from,
    validTo: rate.valid_to || '',
  }))
}

function mapRatesToPayload(rates: TaxCodeForm['rates']) {
  return rates.map((rate) => ({
    rate_percent: Number(rate.ratePercent),
    valid_from: rate.validFrom,
    valid_to: rate.validTo || null,
  }))
}

function applyTaxCodeToForm(row: TaxCodeRead) {
  form.value = {
    name: row.name || '',
    countryId: row.country_id ?? row.country?.id ?? null,
    rates: mapRatesToForm(row.rates),
  }
  message.value = ''
}

function clearFormState() {
  form.value = {
    name: '',
    countryId: null,
    rates: [emptyRate()],
  }
  message.value = ''
}

function addRateRow() {
  form.value.rates.push(emptyRate())
}

function removeRateRow(index: number) {
  form.value.rates.splice(index, 1)
}

async function fetchTaxCodes() {
  try {
    taxCodes.value = await apiJson<TaxCodeRead[]>('/tax-codes/')
  } catch {
    message.value = t('taxCodes.loadError')
    messageType.value = 'error'
  }
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
  let row = taxCodes.value.find((taxCode) => Number(taxCode.id) === Number(id))
  if (!row) {
    try {
      row = await apiJson<TaxCodeRead>(`/tax-codes/${id}`)
    } catch {
      message.value = t('taxCodes.notFound')
      messageType.value = 'error'
      goToList()
      return
    }
  }
  applyTaxCodeToForm(row)
}

watch(() => [route.name, route.params.id], syncRouteToForm, { immediate: true })

function resetForm() {
  goToList()
}

function openCreateForm() {
  if (!props.isAdmin) return
  goToCreate()
}

function onTaxCodeRowClick(_event: Event, { item }: { item: TaxCodeRead }) {
  openDetail(item)
}

function openDetail(row: TaxCodeRead) {
  applyTaxCodeToForm(row)
  goToDetail(row.id)
}

async function saveTaxCode() {
  if (!props.isAdmin) return
  if (!(await validateForm(formRef))) return
  const payload = {
    name: form.value.name.trim(),
    country_id: form.value.countryId,
    rates: mapRatesToPayload(form.value.rates),
  }
  try {
    const path = editMode.value ? `/tax-codes/${routeEntityId.value}` : '/tax-codes/'
    const method = editMode.value ? 'PUT' : 'POST'
    const body = editMode.value
      ? { name: payload.name, country_id: payload.country_id, rates: payload.rates }
      : payload
    await apiJson(path, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    await fetchTaxCodes()
    message.value = editMode.value ? t('taxCodes.updated') : t('taxCodes.created')
    messageType.value = 'success'
    await goToList()
  } catch (error: unknown) {
    message.value = getErrorMessage(error, t('taxCodes.saveError'))
    messageType.value = 'error'
  }
}

async function deleteTaxCodeRow(id: number) {
  if (!props.isAdmin) return
  if (!confirm(t('taxCodes.deleteConfirm'))) return
  try {
    await apiJson(`/tax-codes/${id}`, { method: 'DELETE' })
    await fetchTaxCodes()
    message.value = t('taxCodes.deleted')
    messageType.value = 'success'
    if (Number(routeEntityId.value) === Number(id)) {
      await goToList()
    }
  } catch (error: unknown) {
    message.value = getErrorMessage(error, t('taxCodes.deleteError'))
    messageType.value = 'error'
  }
}

async function deleteTaxCode() {
  if (!routeEntityId.value) return
  await deleteTaxCodeRow(routeEntityId.value)
}

onMounted(async () => {
  await fetchCountries()
  await fetchTaxCodes()
})
</script>

<style scoped>
h2,
h3 {
  margin: 0 0 1rem;
  color: rgb(var(--v-theme-on-surface));
}

.rates-block {
  margin: 1.5rem 0;
}

.rates-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.rate-row {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr auto;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
  align-items: start;
}

.muted {
  color: rgba(var(--v-theme-on-surface), 0.65);
  font-size: 0.875rem;
  margin: 0 0 1rem;
}

.table-header span {
  opacity: 0.7;
  font-size: 0.9rem;
}

@media (max-width: 900px) {
  .rate-row {
    grid-template-columns: 1fr;
  }
}
</style>
