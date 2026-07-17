<template>
  <div class="event-stock-tab">
    <p v-if="loadError" class="error">{{ loadError }}</p>
    <p v-else-if="loading" class="muted">{{ $t('common.loading') }}</p>
    <template v-else>
      <section v-if="ingredientsLocal.length" class="stock-group ingredients-group">
        <h3>{{ $t('events.tabs.ingredientsTitle') }}</h3>
        <VqDataTable
          :headers="ingredientHeaders"
          :items="ingredientsLocal"
          item-value="id"
          hide-default-footer
          class="vq-data-table list-table nested stock-table"
        >
          <template #item.unit="{ item }">
            {{ item.unit || $t('common.emDash') }}
          </template>
          <template #item.monitor_stock="{ item }">
            <v-checkbox v-model="item.monitor_stock" hide-details density="compact" />
          </template>
          <template #item.initial_in_stock="{ item }">
            <v-text-field
              v-model.number="item.initial_in_stock"
              type="number"
              min="0"
              step="any"
              :disabled="!item.monitor_stock"
              hide-details
              density="compact"
              class="stock-qty-input"
            />
          </template>
          <template #item.in_stock="{ item }">
            <v-text-field
              v-model.number="item.in_stock"
              type="number"
              min="0"
              step="any"
              :disabled="!item.monitor_stock"
              hide-details
              density="compact"
              class="stock-qty-input"
            />
          </template>
        </VqDataTable>
      </section>

      <p v-if="!itemsLocal.length && !ingredientsLocal.length" class="muted">
        {{ $t('events.tabs.noStockArticles') }}
      </p>
      <template v-else-if="itemsLocal.length">
        <section v-for="group in stockGroups" :key="group.key" class="stock-group">
          <h3>{{ group.name }}</h3>
          <VqDataTable
            :headers="stockHeaders"
            :items="group.items"
            item-value="id"
            hide-default-footer
            class="vq-data-table list-table nested stock-table"
          >
            <template #item.monitor_stock="{ item }">
              <v-checkbox v-model="item.monitor_stock" hide-details density="compact" />
            </template>
            <template #item.initial_in_stock="{ item }">
              <v-text-field
                v-model.number="item.initial_in_stock"
                type="number"
                min="0"
                :disabled="!item.monitor_stock"
                hide-details
                density="compact"
                class="stock-qty-input"
              />
            </template>
            <template #item.in_stock="{ item }">
              <v-text-field
                v-model.number="item.in_stock"
                type="number"
                min="0"
                :disabled="!item.monitor_stock"
                hide-details
                density="compact"
                class="stock-qty-input"
              />
            </template>
          </VqDataTable>
        </section>
      </template>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { apiJson } from '../api'
import { stockGroupsForItems } from '@vendiqo/frontend-shared/stockByStation'
import { useDirtyAutosave } from '../composables/useDirtyAutosave'
import VqDataTable from './VqDataTable.vue'
import type { EventStockListRead, EventStockUpdateIn } from '@/types/api'
import { getErrorMessage } from '@/types/api'
import type {
  EventStationLocal,
  EventStockItemLocal,
  EventIngredientStockItemLocal,
  SaveStatus,
  StatusChangePayload,
} from '@/types/ui'
import type { DataTableHeader } from '@/types/vuetify'

const { t } = useI18n()

const props = withDefaults(
  defineProps<{
    eventId: number
    stations?: EventStationLocal[]
  }>(),
  {
    stations: () => [],
  },
)

const emit = defineEmits<{
  'status-change': [payload: StatusChangePayload]
}>()

const COL_NAME = { minWidth: '12rem' }
const COL_UNIT = { width: '6rem', sortable: false }
const COL_MONITOR = { width: '9rem', sortable: false, align: 'center' as const }
const COL_QTY = { width: '8rem', sortable: false, align: 'end' as const }

const stockHeaders = computed((): DataTableHeader[] => [
  { title: t('events.tabs.article'), key: 'name', ...COL_NAME },
  { title: t('events.tabs.monitorStock'), key: 'monitor_stock', ...COL_MONITOR },
  { title: t('events.tabs.initialStock'), key: 'initial_in_stock', ...COL_QTY },
  { title: t('events.tabs.currentStock'), key: 'in_stock', ...COL_QTY },
])

const ingredientHeaders = computed((): DataTableHeader[] => [
  { title: t('events.tabs.ingredient'), key: 'name', ...COL_NAME },
  { title: t('common.unit'), key: 'unit', ...COL_UNIT },
  { title: t('events.tabs.monitorStock'), key: 'monitor_stock', ...COL_MONITOR },
  { title: t('events.tabs.initialStock'), key: 'initial_in_stock', ...COL_QTY },
  { title: t('events.tabs.currentStock'), key: 'in_stock', ...COL_QTY },
])

const loading = ref(true)
const loadError = ref('')
const itemsLocal = ref<EventStockItemLocal[]>([])
const ingredientsLocal = ref<EventIngredientStockItemLocal[]>([])

const stockGroups = computed(() =>
  stockGroupsForItems(itemsLocal.value, props.stations as Parameters<typeof stockGroupsForItems>[1]),
)

function stockPayloadSnapshot(): EventStockUpdateIn {
  return {
    ingredients: ingredientsLocal.value.map((row) => ({
      ingredient_id: row.id,
      monitor_stock: !!row.monitor_stock,
      initial_in_stock: row.monitor_stock ? (row.initial_in_stock ?? 0) : null,
      in_stock: row.monitor_stock ? (row.in_stock ?? 0) : null,
    })),
    items: itemsLocal.value.map((row) => ({
      article_id: row.id,
      monitor_stock: !!row.monitor_stock,
      initial_in_stock: row.monitor_stock ? (row.initial_in_stock ?? 0) : null,
      in_stock: row.monitor_stock ? (row.in_stock ?? 0) : null,
    })),
  }
}

const stockWatchSource = computed(() => stockPayloadSnapshot())

function applyStockItems(data: EventStockListRead) {
  ingredientsLocal.value = (data.ingredients || []).map((row) => ({
    id: row.id,
    name: row.name,
    unit: row.unit ?? null,
    monitor_stock: !!row.monitor_stock,
    initial_in_stock: row.monitor_stock ? (row.initial_in_stock ?? row.in_stock ?? 0) : 0,
    in_stock: row.monitor_stock ? (row.in_stock ?? 0) : 0,
  }))
  itemsLocal.value = (data.items || []).map((row) => ({
    id: row.id,
    name: row.name,
    label: row.label,
    monitor_stock: !!row.monitor_stock,
    initial_in_stock: row.monitor_stock ? (row.initial_in_stock ?? row.in_stock ?? 0) : 0,
    in_stock: row.monitor_stock ? (row.in_stock ?? 0) : 0,
  }))
}

async function persistStock(): Promise<boolean> {
  if (!props.eventId) return false
  const data = await apiJson<EventStockListRead>(`/events/${props.eventId}/event-stock`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(stockPayloadSnapshot()),
  })
  applyStockItems(data)
  return true
}

const autosaveEnabled = computed(() => !!props.eventId && !loading.value)

const {
  status: autosaveStatus,
  errorMessage: autosaveError,
  markSaved,
  resetSnapshot,
  flush,
  setError,
} = useDirtyAutosave({
  getSnapshot: stockPayloadSnapshot,
  saveFn: async () => {
    try {
      return await persistStock()
    } catch (e: unknown) {
      setError(getErrorMessage(e, t('events.tabs.saveFailed')))
      return false
    }
  },
  watchSource: stockWatchSource,
  enabled: autosaveEnabled,
})

watch([autosaveStatus, autosaveError], () => {
  emit('status-change', {
    status: autosaveStatus.value as SaveStatus,
    errorMessage: autosaveError.value,
  })
}, { immediate: true })

async function loadStock() {
  if (!props.eventId) return
  loading.value = true
  loadError.value = ''
  resetSnapshot()
  try {
    const data = await apiJson<EventStockListRead>(`/events/${props.eventId}/event-stock`)
    applyStockItems(data)
    markSaved()
  } catch (e: unknown) {
    loadError.value = getErrorMessage(e, t('events.tabs.loadFailed'))
    itemsLocal.value = []
    ingredientsLocal.value = []
  } finally {
    loading.value = false
  }
}

watch(
  () => props.eventId,
  () => {
    loadStock()
  },
  { immediate: true },
)

defineExpose({
  autosaveStatus,
  autosaveError,
  flush,
  isDirty: () => autosaveStatus.value === 'dirty' || autosaveStatus.value === 'error',
})
</script>

<style scoped>
.stock-qty-input {
  max-width: 8rem;
}
.stock-group {
  margin-bottom: 1.5rem;
}
.stock-group h3 {
  margin: 0 0 0.75rem;
  font-size: 1rem;
  font-weight: 600;
}
.muted {
  opacity: 0.7;
}

.event-stock-tab :deep(.stock-table table) {
  table-layout: fixed;
  width: 100%;
}

.event-stock-tab :deep(.stock-table th),
.event-stock-tab :deep(.stock-table td) {
  overflow: hidden;
  text-overflow: ellipsis;
}

.event-stock-tab :deep(.stock-table th:nth-child(1)),
.event-stock-tab :deep(.stock-table td:nth-child(1)) {
  width: auto;
}

.event-stock-tab :deep(.stock-table th:nth-child(2)),
.event-stock-tab :deep(.stock-table td:nth-child(2)) {
  width: 9rem;
}

.event-stock-tab :deep(.stock-table th:nth-child(3)),
.event-stock-tab :deep(.stock-table td:nth-child(3)),
.event-stock-tab :deep(.stock-table th:nth-child(4)),
.event-stock-tab :deep(.stock-table td:nth-child(4)) {
  width: 8rem;
}

.ingredients-group :deep(.stock-table th:nth-child(2)),
.ingredients-group :deep(.stock-table td:nth-child(2)) {
  width: 6rem;
}

.ingredients-group :deep(.stock-table th:nth-child(3)),
.ingredients-group :deep(.stock-table td:nth-child(3)) {
  width: 9rem;
}

.ingredients-group :deep(.stock-table th:nth-child(4)),
.ingredients-group :deep(.stock-table td:nth-child(4)),
.ingredients-group :deep(.stock-table th:nth-child(5)),
.ingredients-group :deep(.stock-table td:nth-child(5)) {
  width: 8rem;
}

@media (max-width: 992px) {
  .stock-qty-input {
    max-width: 100%;
  }
}
</style>
