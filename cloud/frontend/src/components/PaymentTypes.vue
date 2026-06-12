<template>
  <ListDetailLayout
    :title="$t('paymentTypes.title')"
    :subtitle="$t('paymentTypes.subtitle')"
    :createLabel="$t('paymentTypes.createLabel')"
    :showCreate="isAdmin"
    :showDetail="showDetail"
    @open-create="openCreateForm"
  >
    <template #detail>
      <h2>{{ editMode ? $t('paymentTypes.editTitle') : $t('paymentTypes.newTitle') }}</h2>
      <p class="form-required-legend"><span class="vq-asterisk">*</span> {{ $t('common.requiredLegend') }}</p>

      <v-form ref="formRef" @submit.prevent="savePaymentType">
        <div class="form-field">
          <FormLabel required>{{ $t('paymentTypes.slug') }}</FormLabel>
          <v-text-field
            v-model="form.slug"
            :placeholder="$t('paymentTypes.slugPlaceholder')"
            hide-details="auto"
            :readonly="!isAdmin"
            required
            :rules="[rules.required]"
          />
          <small class="muted">{{ $t('paymentTypes.slugHint') }}</small>
        </div>
        <div class="form-field">
          <v-text-field
            v-model.number="form.sortOrder"
            type="number"
            :label="$t('paymentTypes.sortOrder')"
            hide-details="auto"
            :readonly="!isAdmin"
            required
            :rules="[rules.requiredNumber]"
          />
        </div>
        <v-checkbox
          v-model="form.isActive"
          :label="$t('paymentTypes.isActive')"
          hide-details
          density="compact"
          :readonly="!isAdmin"
        />

        <div v-if="isAdmin" class="actions">
          <v-btn variant="outlined" type="button" @click="resetForm">{{ $t('common.back') }}</v-btn>
          <v-btn color="primary" type="submit">{{ $t('common.save') }}</v-btn>
        </div>
        <p v-if="message" :class="messageType">{{ message }}</p>
      </v-form>
    </template>

    <template #table>
      <div class="table-header">
        <h2>{{ $t('paymentTypes.allTitle') }}</h2>
        <span>{{ $t('common.entriesCountTotal', { total: paymentTypes.length }) }}</span>
      </div>

      <VqDataTable
        v-model:page="currentPage"
        :headers="tableHeaders"
        :items="paymentTypes"
        :items-per-page="pageSize"
        item-value="id"
        hover
        :no-data-text="$t('paymentTypes.noData')"
        class="vq-data-table list-table"
        @click:row="(_e, { item }) => openDetail(item)"
      >
        <template #item.label="{ item }">
          {{ paymentTypeLabel(item.slug) }}
        </template>
        <template #item.is_active="{ item }">
          {{ item.is_active ? $t('common.yes') : $t('common.no') }}
        </template>
        <template #item.actions="{ item }">
          <v-btn v-if="isAdmin" color="error" variant="text" @click.stop="deletePaymentType(item.id)">
            {{ $t('common.delete') }}
          </v-btn>
        </template>
      </VqDataTable>
    </template>
  </ListDetailLayout>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import FormLabel from './FormLabel.vue'
import ListDetailLayout from './ListDetailLayout.vue'
import VqDataTable from './VqDataTable.vue'
import { apiFetch } from '../api'
import { parseApiErrorDetail } from '../utils/apiError.js'
import { rules, validateForm } from '../utils/formRules.js'
import { useListDetailRouting } from '../composables/useListDetailRouting'
import { useClientPagination } from '../composables/useClientPagination'
import { invalidatePaymentTypesCache, paymentTypeLabel as labelForSlug } from '../composables/usePaymentTypes'

const props = defineProps({
  isAdmin: { type: Boolean, default: false },
})

const { t } = useI18n()
const route = useRoute()
const {
  isCreateMode,
  editMode,
  showDetail,
  routeEntityId,
  goToList,
  goToCreate,
  goToDetail,
} = useListDetailRouting('payment-types')

const paymentTypes = ref([])
const message = ref('')
const messageType = ref('')
const formRef = ref(null)

const form = ref({
  slug: '',
  sortOrder: 0,
  isActive: true,
})

const tableHeaders = computed(() => {
  const headers = [
    { title: t('common.id'), key: 'id' },
    { title: t('paymentTypes.slug'), key: 'slug' },
    { title: t('common.label'), key: 'label', sortable: false },
    { title: t('paymentTypes.sortOrder'), key: 'sort_order' },
    { title: t('paymentTypes.isActive'), key: 'is_active', sortable: false },
  ]
  if (props.isAdmin) {
    headers.push({ title: t('common.actions'), key: 'actions', sortable: false, align: 'end' })
  }
  return headers
})

function paymentTypeLabel(slug) {
  return labelForSlug(slug, t)
}

const { currentPage, pageSize } = useClientPagination(paymentTypes)

function applyToForm(row) {
  form.value = {
    slug: row.slug || '',
    sortOrder: row.sort_order ?? 0,
    isActive: Boolean(row.is_active),
  }
  message.value = ''
}

function clearFormState() {
  form.value = { slug: '', sortOrder: 0, isActive: true }
  message.value = ''
}

async function fetchPaymentTypes() {
  try {
    const response = await apiFetch('/payment-types/')
    if (!response.ok) throw new Error(await response.text())
    paymentTypes.value = await response.json()
  } catch {
    message.value = t('paymentTypes.loadError')
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
  let row = paymentTypes.value.find((item) => Number(item.id) === Number(id))
  if (!row) {
    try {
      const response = await apiFetch(`/payment-types/${id}`)
      if (!response.ok) throw new Error(await response.text())
      row = await response.json()
    } catch {
      message.value = t('paymentTypes.notFound')
      messageType.value = 'error'
      goToList()
      return
    }
  }
  applyToForm(row)
}

watch(() => [route.name, route.params.id], syncRouteToForm, { immediate: true })

function resetForm() {
  goToList()
}

function openCreateForm() {
  goToCreate()
}

function openDetail(item) {
  applyToForm(item)
  goToDetail(item.id)
}

async function savePaymentType() {
  if (!props.isAdmin) return
  if (!(await validateForm(formRef))) return
  const payload = {
    slug: form.value.slug.trim().toLowerCase(),
    sort_order: Number(form.value.sortOrder),
    is_active: form.value.isActive,
  }
  try {
    const path = editMode.value ? `/payment-types/${routeEntityId.value}` : '/payment-types/'
    const method = editMode.value ? 'PUT' : 'POST'
    const response = await apiFetch(path, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      throw new Error(parseApiErrorDetail(err.detail) || t('paymentTypes.saveError'))
    }
    invalidatePaymentTypesCache()
    await fetchPaymentTypes()
    message.value = editMode.value ? t('paymentTypes.updated') : t('paymentTypes.created')
    messageType.value = 'success'
    await goToList()
  } catch (error) {
    message.value = error.message || t('paymentTypes.saveError')
    messageType.value = 'error'
  }
}

async function deletePaymentType(id) {
  if (!confirm(t('paymentTypes.deleteConfirm'))) return
  try {
    const response = await apiFetch(`/payment-types/${id}`, { method: 'DELETE' })
    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      throw new Error(parseApiErrorDetail(err.detail) || t('paymentTypes.deleteError'))
    }
    invalidatePaymentTypesCache()
    await fetchPaymentTypes()
    message.value = t('paymentTypes.deleted')
    messageType.value = 'success'
    if (Number(routeEntityId.value) === Number(id)) {
      await goToList()
    }
  } catch (error) {
    message.value = error.message || t('paymentTypes.deleteError')
    messageType.value = 'error'
  }
}

onMounted(fetchPaymentTypes)
</script>

<style scoped>
h2 {
  margin: 0 0 1.5rem;
}

.form-field {
  margin-bottom: 1rem;
}

.table-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.table-header h2 {
  margin: 0;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 1.25rem;
}
</style>
