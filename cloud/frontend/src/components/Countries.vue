<template>
  <ListDetailLayout
    :title="$t('countries.title')"
    :subtitle="$t('countries.subtitle')"
    :createLabel="$t('countries.createLabel')"
    :showCreate="isAdmin"
    :showDetail="showDetail"
    @open-create="openCreateForm"
  >
    <template #detail>
      <h2>{{ editMode ? $t('countries.editTitle') : $t('countries.newTitle') }}</h2>
      <p class="form-required-legend"><span class="vq-asterisk">*</span> {{ $t('common.requiredLegend') }}</p>

      <v-form ref="formRef" @submit.prevent="saveCountry">
        <div class="form-field">
          <FormLabel required>{{ $t('countries.code') }}</FormLabel>
          <v-text-field
            v-model="form.code"
            :placeholder="$t('countries.codePlaceholder')"
            hide-details="auto"
            maxlength="2"
            :readonly="!isAdmin"
            required
            :rules="[rules.required]"
          />
        </div>
        <div class="form-field">
          <FormLabel required>{{ $t('common.name') }}</FormLabel>
          <v-text-field
            v-model="form.name"
            :placeholder="$t('countries.namePlaceholder')"
            hide-details="auto"
            :readonly="!isAdmin"
            required
            :rules="[rules.required]"
          />
        </div>
        <div v-if="isAdmin" class="actions">
          <v-btn variant="outlined" type="button" @click="resetForm">{{ $t('common.back') }}</v-btn>
          <v-btn v-if="editMode" color="error" variant="outlined" type="button" @click="deleteCountry">
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
        <h2>{{ $t('countries.allTitle') }}</h2>
        <span>{{ $t('common.entriesCountTotal', { total: countries.length }) }}</span>
      </div>
      <VqDataTable
        :headers="tableHeaders"
        :items="countries"
        item-value="id"
        hover
        hide-default-footer
        :no-data-text="$t('countries.noData')"
        class="vq-data-table list-table"
        @click:row="onCountryRowClick"
      >
        <template v-if="isAdmin" #item.actions="{ item }">
          <v-btn color="error" @click.stop="deleteCountryRowFromTable(item)">
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
import { rules, validateForm } from '../utils/formRules.js'
import { useCountries } from '../composables/useCountries'
import { useListDetailRouting } from '../composables/useListDetailRouting'
import type { CountryRead, CountryCreate } from '@/types/api'
import { isApiError } from '@/types/api'
import type { DataTableHeader } from '@/types/vuetify'
import type { ValidatableForm } from '../utils/formRules.js'

const props = defineProps<{
  isAdmin?: boolean
}>()

const { t } = useI18n()
const route = useRoute()
const { countries, fetchCountries, invalidateCountries } = useCountries()
const {
  isCreateMode,
  editMode,
  showDetail,
  routeEntityId,
  goToList,
  goToCreate,
  goToDetail,
} = useListDetailRouting('countries')

const tableHeaders = computed((): DataTableHeader[] => {
  const headers: DataTableHeader[] = [
    { title: t('common.id'), key: 'id' },
    { title: t('countries.code'), key: 'code' },
    { title: t('common.name'), key: 'name' },
  ]
  if (props.isAdmin) {
    headers.push({ title: t('common.actions'), key: 'actions', sortable: false, align: 'end' })
  }
  return headers
})

const message = ref('')
const messageType = ref('')
const formRef = ref<ValidatableForm | null>(null)
const form = ref({ code: '', name: '' })

const emptyForm = () => ({ code: '', name: '' })

function applyCountryToForm(row: CountryRead) {
  form.value = {
    code: row.code || '',
    name: row.name || '',
  }
  message.value = ''
}

function clearFormState() {
  form.value = emptyForm()
  message.value = ''
}

async function loadCountries() {
  try {
    await fetchCountries({ force: true })
  } catch {
    message.value = t('countries.loadError')
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
  let row = countries.value.find((country) => Number(country.id) === Number(id))
  if (!row) {
    try {
      row = await apiJson<CountryRead>(`/countries/${id}`)
    } catch {
      message.value = t('countries.notFound')
      messageType.value = 'error'
      goToList()
      return
    }
  }
  applyCountryToForm(row)
}

watch(() => [route.name, route.params.id], syncRouteToForm, { immediate: true })

function resetForm() {
  goToList()
}

function openCreateForm() {
  if (!props.isAdmin) return
  goToCreate()
}

function openDetail(row: CountryRead) {
  applyCountryToForm(row)
  goToDetail(row.id)
}

function onCountryRowClick(_event: Event, { item }: { item: CountryRead }) {
  openDetail(item)
}

function deleteCountryRowFromTable(item: CountryRead) {
  return deleteCountryRow(item.id)
}

async function saveCountry() {
  if (!props.isAdmin) return
  if (!(await validateForm(formRef))) return
  const payload: CountryCreate = {
    code: form.value.code.trim().toUpperCase(),
    name: form.value.name.trim(),
  }
  try {
    const path = editMode.value ? `/countries/${routeEntityId.value}` : '/countries/'
    const method = editMode.value ? 'PUT' : 'POST'
    await apiJson(path, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    invalidateCountries()
    await loadCountries()
    message.value = editMode.value ? t('countries.updated') : t('countries.created')
    messageType.value = 'success'
    await goToList()
  } catch (error: unknown) {
    message.value = isApiError(error) ? error.message || t('countries.saveError') : t('countries.saveError')
    messageType.value = 'error'
  }
}

async function deleteCountryRow(id: number | string) {
  if (!props.isAdmin) return
  if (!confirm(t('countries.deleteConfirm'))) return
  try {
    await apiJson(`/countries/${id}`, { method: 'DELETE' })
    invalidateCountries()
    await loadCountries()
    message.value = t('countries.deleted')
    messageType.value = 'success'
    if (Number(routeEntityId.value) === Number(id)) {
      await goToList()
    }
  } catch (error: unknown) {
    message.value = isApiError(error) ? error.message || t('countries.deleteError') : t('countries.deleteError')
    messageType.value = 'error'
  }
}

async function deleteCountry() {
  if (!routeEntityId.value) return
  await deleteCountryRow(routeEntityId.value)
}

onMounted(loadCountries)
</script>

<style scoped>
h2 {
  margin: 0 0 1.5rem;
  color: rgb(var(--v-theme-on-surface));
}

.table-header span {
  opacity: 0.7;
  font-size: 0.9rem;
}
</style>
