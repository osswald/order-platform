<template>
  <ListDetailLayout
    :title="$t('waiters.title')"
    :subtitle="$t('waiters.subtitle')"
    :createLabel="$t('waiters.createLabel')"
    :showCreate="canCreateWaiters"
    :showDetail="showDetail"
    @open-create="openCreateForm"
  >
    <template #header-actions>
      <HelpLink slug="waiters" variant="icon" />
    </template>
    <template #detail>
      <h2>{{ editMode ? $t('waiters.editTitle') : $t('waiters.newTitle') }}</h2>
      <p class="form-required-legend"><span class="vq-asterisk">*</span> {{ $t('common.requiredLegend') }}</p>

      <v-form ref="formRef" @submit.prevent="saveWaiter">
        <div class="form-field">
          <FormLabel required>{{ $t('common.name') }}</FormLabel>
          <v-text-field
            v-model="form.name"
            :placeholder="$t('waiters.namePlaceholder')"
            hide-details="auto"
            required
            :rules="[rules.required]"
          />
        </div>

        <div class="form-field">
          <FormLabel required>{{ $t('common.pin') }}</FormLabel>
          <v-text-field
            v-model="form.pin"
            :placeholder="$t('waiters.pinPlaceholder')"
            hide-details="auto"
            required
            :rules="[rules.required]"
          />
          <small>{{ $t('waiters.pinHint') }}</small>
        </div>

        <div class="actions">
          <v-btn variant="outlined" type="button" @click="resetForm">{{ $t('common.back') }}</v-btn>
          <v-btn color="primary" type="submit">{{ $t('common.save') }}</v-btn>
        </div>
        <p v-if="message" :class="messageType">{{ message }}</p>
      </v-form>
    </template>

    <template #table>
      <p v-if="activeOrganisationId == null" class="empty-hint">
        {{ $t('common.noOrganisation') }}
      </p>
      <div class="table-header">
        <h2>{{ $t('waiters.allTitle') }}</h2>
        <span>{{ $t('common.entriesCount', { filtered: filteredWaiters.length, total: waitersInActiveOrganisation.length }) }}</span>
      </div>
      <div class="list-controls">
        <div class="search-field">
          <label>{{ $t('common.search') }}</label>
          <v-text-field
            v-model="searchQuery"
            :placeholder="$t('waiters.searchPlaceholder')"
            prepend-inner-icon="mdi-magnify"
            hide-details="auto"
          />
        </div>
      </div>

      <VqDataTable
        v-model:page="currentPage"
        :headers="tableHeaders"
        :items="filteredWaiters"
        :items-per-page="pageSize"
        item-value="id"
        hover
        :no-data-text="$t('waiters.noData')"
        class="vq-data-table list-table"
        @click:row="onWaiterRowClick"
      >
        <template #item.actions="{ item }">
          <v-btn color="error" variant="text" @click.stop="deleteWaiter(item.id)">{{ $t('common.delete') }}</v-btn>
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
import { apiJson } from '../api'
import { rules, validateForm, type ValidatableForm } from '../utils/formRules.js'
import { useListDetailRouting } from '../composables/useListDetailRouting'
import { useClientPagination } from '../composables/useClientPagination'
import { invalidateOrgCatalog } from '../composables/useOrgCatalog'
import { matchesActiveOrganisation } from '../utils/orgScope'
import { waiterListHeaders } from '../utils/orgScopedListTableHeaders'
import VqDataTable from './VqDataTable.vue'
import HelpLink from './HelpLink.vue'
import type { WaiterRead } from '@/types/api'
import type { WaiterForm } from '@/types/ui'
import type { DataTableHeader } from '@/types/vuetify'

const { t } = useI18n()

const props = defineProps<{
  activeOrganisationId?: number | null
}>()

const route = useRoute()
const {
  isCreateMode,
  editMode,
  showDetail,
  routeEntityId,
  goToList,
  goToCreate,
  goToDetail,
} = useListDetailRouting('waiters')

const tableHeaders = computed((): DataTableHeader[] => waiterListHeaders(t))

const waiters = ref<WaiterRead[]>([])
const message = ref('')
const messageType = ref('')
const searchQuery = ref('')

const emptyForm = (): WaiterForm => ({
  name: '',
  pin: '0000',
})

const form = ref<WaiterForm>(emptyForm())
const formRef = ref<ValidatableForm | null>(null)

const canCreateWaiters = computed(() => props.activeOrganisationId != null)

function matchesSearch(waiter: WaiterRead, term: string): boolean {
  if (!term) return true
  return [
    waiter.id,
    waiter.name,
    waiter.pin,
    waiter.organisation_name,
  ]
    .filter((value) => value !== null && value !== undefined)
    .some((value) => String(value).toLowerCase().includes(term))
}

const filteredWaiters = computed(() => {
  const term = searchQuery.value.trim().toLowerCase()
  return waiters.value.filter((waiter) => {
    if (!matchesSearch(waiter, term)) return false
    if (!matchesActiveOrganisation(props.activeOrganisationId, waiter.organisation_id)) return false
    return true
  })
})

const { currentPage, pageSize } = useClientPagination(filteredWaiters, {
  resetOn: [searchQuery, () => props.activeOrganisationId],
})

const waitersInActiveOrganisation = computed(() =>
  waiters.value.filter((waiter) =>
    matchesActiveOrganisation(props.activeOrganisationId, waiter.organisation_id),
  ),
)

async function fetchWaiters() {
  try {
    waiters.value = await apiJson<WaiterRead[]>('/waiters/')
  } catch {
    message.value = t('waiters.loadError')
    messageType.value = 'error'
  }
}

function applyWaiterToForm(waiter: WaiterRead) {
  form.value = {
    name: waiter.name || '',
    pin: waiter.pin || '0000',
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
  let row = waiters.value.find((w) => Number(w.id) === Number(id))
  if (!row) {
    try {
      row = await apiJson<WaiterRead>(`/waiters/${id}`)
    } catch {
      message.value = t('waiters.notFound')
      messageType.value = 'error'
      goToList()
      return
    }
  }
  applyWaiterToForm(row)
}

watch(() => [route.name, route.params.id], syncRouteToForm, { immediate: true })

function resetForm() {
  goToList()
}

function openCreateForm() {
  goToCreate()
}

function onWaiterRowClick(_event: Event, { item }: { item: WaiterRead }) {
  editWaiter(item)
}

function editWaiter(waiter: WaiterRead) {
  applyWaiterToForm(waiter)
  goToDetail(waiter.id)
}

async function saveWaiter() {
  if (props.activeOrganisationId == null) {
    message.value = t('common.noOrganisation')
    messageType.value = 'error'
    return
  }
  if (!(await validateForm(formRef))) return
  const payload: { name: string; pin: string; organisation_id?: number } = {
    name: form.value.name,
    pin: form.value.pin || '0000',
  }
  if (!editMode.value) {
    payload.organisation_id = props.activeOrganisationId!
  }

  try {
    const path = editMode.value ? `/waiters/${routeEntityId.value}` : '/waiters/'
    const method = editMode.value ? 'PUT' : 'POST'
    await apiJson(path, {
      method,
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })
    const wasEdit = editMode.value
    await fetchWaiters()
    invalidateOrgCatalog(props.activeOrganisationId)
    message.value = wasEdit ? t('waiters.updated') : t('waiters.created')
    messageType.value = 'success'
    await goToList()
  } catch {
    message.value = t('waiters.saveError')
    messageType.value = 'error'
  }
}

async function deleteWaiter(id: number) {
  if (!confirm(t('waiters.deleteConfirm'))) return
  try {
    await apiJson(`/waiters/${id}`, {
      method: 'DELETE',
    })
    await fetchWaiters()
    invalidateOrgCatalog(props.activeOrganisationId)
    message.value = t('waiters.deleted')
    messageType.value = 'success'
    if (Number(routeEntityId.value) === Number(id)) {
      await goToList()
    }
  } catch {
    message.value = t('waiters.deleteError')
    messageType.value = 'error'
  }
}

onMounted(fetchWaiters)
</script>

<style scoped>
.empty-hint {
  opacity: 0.7;
  margin: 0 0 1rem;
}

h2 {
  margin: 0 0 1.5rem;
  color: rgb(var(--v-theme-on-surface));
}

label {
  color: rgb(var(--v-theme-on-surface));
  font-size: 0.875rem;
  font-weight: 600;
}

small,
.table-header span {
  opacity: 0.7;
  font-size: 0.9rem;
}

.actions {
  justify-content: flex-end;
  margin-top: 1.25rem;
}

.table-header h2 {
  margin: 0;
}

.search-field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
</style>
