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
        @click:row="onPaymentTypeRowClick"
      >
        <template #item.label="{ item }">
          {{ paymentTypeLabel(item.slug) }}
        </template>
        <template #item.is_active="{ item }">
          {{ item.is_active ? $t('common.yes') : $t('common.no') }}
        </template>
        <template #item.actions="{ item }">
          <v-btn v-if="isAdmin" color="error" @click.stop="deletePaymentType(item.id)">
            {{ $t('common.delete') }}
          </v-btn>
        </template>
      </VqDataTable>
    </template>
  </ListDetailLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import FormLabel from './FormLabel.vue'
import ListDetailLayout from './ListDetailLayout.vue'
import VqDataTable from './VqDataTable.vue'
import { apiJson } from '../api'
import { rules, validateForm, type ValidatableForm } from '../utils/formRules.js'
import { useListDetailRouting } from '../composables/useListDetailRouting'
import { useClientPagination } from '../composables/useClientPagination'
import { invalidatePaymentTypesCache, paymentTypeLabel as labelForSlug } from '../composables/usePaymentTypes'
import type { PaymentTypeRead } from '@/types/api'
import { getErrorMessage } from '@/types/api'
import type { PaymentTypeForm } from '@/types/ui'
import type { DataTableHeader } from '@/types/vuetify'

const props = defineProps<{
  isAdmin?: boolean
}>()

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

const paymentTypes = ref<PaymentTypeRead[]>([])
const message = ref('')
const messageType = ref('')
const formRef = ref<ValidatableForm | null>(null)

const form = ref<PaymentTypeForm>({
  slug: '',
  sortOrder: 0,
  isActive: true,
})

const tableHeaders = computed((): DataTableHeader[] => {
  const headers: DataTableHeader[] = [
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

function paymentTypeLabel(slug: string): string {
  return labelForSlug(slug, t)
}

const { currentPage, pageSize } = useClientPagination(paymentTypes)

function applyToForm(row: PaymentTypeRead) {
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
    paymentTypes.value = await apiJson<PaymentTypeRead[]>('/payment-types/')
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
      row = await apiJson<PaymentTypeRead>(`/payment-types/${id}`)
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

function onPaymentTypeRowClick(_event: Event, { item }: { item: PaymentTypeRead }) {
  openDetail(item)
}

function openDetail(item: PaymentTypeRead) {
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
    await apiJson(path, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    invalidatePaymentTypesCache()
    await fetchPaymentTypes()
    message.value = editMode.value ? t('paymentTypes.updated') : t('paymentTypes.created')
    messageType.value = 'success'
    await goToList()
  } catch (error: unknown) {
    message.value = getErrorMessage(error, t('paymentTypes.saveError'))
    messageType.value = 'error'
  }
}

async function deletePaymentType(id: number) {
  if (!confirm(t('paymentTypes.deleteConfirm'))) return
  try {
    await apiJson(`/payment-types/${id}`, { method: 'DELETE' })
    invalidatePaymentTypesCache()
    await fetchPaymentTypes()
    message.value = t('paymentTypes.deleted')
    messageType.value = 'success'
    if (Number(routeEntityId.value) === Number(id)) {
      await goToList()
    }
  } catch (error: unknown) {
    message.value = getErrorMessage(error, t('paymentTypes.deleteError'))
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
