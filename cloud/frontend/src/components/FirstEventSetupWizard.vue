<template>
  <section class="vq-page panel first-event-setup-wizard">
    <div class="vq-page-header panel-header">
      <div>
        <h1>{{ t('firstEventSetup.wizard.title') }}</h1>
        <p>{{ t('firstEventSetup.wizard.subtitle') }}</p>
      </div>
      <v-btn variant="outlined" type="button" @click="router.push({ name: 'dashboard' })">
        {{ t('common.cancel') }}
      </v-btn>
    </div>

    <p v-if="!organisationId" class="error">{{ t('common.noOrganisation') }}</p>
    <p v-else-if="bootError" class="error">{{ bootError }}</p>
    <p v-else-if="booting" class="muted">{{ t('common.loading') }}</p>

    <v-card v-else variant="flat" border class="wizard-card">
      <v-stepper v-model="stepIndex" flat>
        <v-stepper-header>
          <template v-for="(step, idx) in FIRST_EVENT_SETUP_STEPS" :key="step">
            <v-divider v-if="idx > 0" />
            <v-stepper-item
              :value="idx + 1"
              :title="t(`firstEventSetup.wizard.steps.${step}`)"
              :complete="stepIndex > idx + 1"
            />
          </template>
        </v-stepper-header>

        <v-stepper-window v-model="stepIndex">
          <v-stepper-window-item :value="1">
            <div class="step-body">
              <p class="muted">{{ t('firstEventSetup.wizard.menuHint') }}</p>
              <template v-if="canSkipMenu">
                <v-alert type="success" density="compact" variant="tonal">
                  {{ t('firstEventSetup.wizard.menuReady', { count: sellableArticles.length }) }}
                </v-alert>
                <v-btn color="primary" type="button" class="mt-3" @click="goNext">
                  {{ t('firstEventSetup.wizard.skipContinue') }}
                </v-btn>
              </template>
              <template v-else>
                <v-text-field
                  v-model="categoryName"
                  :label="t('firstEventSetup.wizard.categoryName')"
                  required
                />
                <div
                  v-for="(row, idx) in articleRows"
                  :key="idx"
                  class="article-row"
                >
                  <v-text-field
                    v-model="row.name"
                    :label="t('firstEventSetup.wizard.articleName')"
                    required
                  />
                  <v-text-field
                    v-model.number="row.price"
                    :label="t('firstEventSetup.wizard.articlePrice')"
                    type="number"
                    min="0"
                    step="0.05"
                    required
                  />
                  <v-btn
                    v-if="articleRows.length > 1"
                    icon="mdi-delete"
                    color="error"
                    type="button"
                    @click="articleRows.splice(idx, 1)"
                  />
                </div>
                <v-btn variant="outlined" type="button" size="small" @click="addArticleRow">
                  {{ t('firstEventSetup.wizard.addArticle') }}
                </v-btn>
              </template>
            </div>
          </v-stepper-window-item>

          <v-stepper-window-item :value="2">
            <div class="step-body">
              <p class="muted">{{ t('firstEventSetup.wizard.waitersHint') }}</p>
              <template v-if="canSkipWaiters">
                <v-alert type="success" density="compact" variant="tonal">
                  {{ t('firstEventSetup.wizard.waitersReady', { count: waiters.length }) }}
                </v-alert>
                <v-btn color="primary" type="button" class="mt-3" @click="goNext">
                  {{ t('firstEventSetup.wizard.skipContinue') }}
                </v-btn>
              </template>
              <template v-else>
                <v-text-field v-model="waiterName" :label="t('firstEventSetup.wizard.waiterName')" required />
                <v-text-field v-model="waiterPin" :label="t('firstEventSetup.wizard.waiterPin')" required />
              </template>
            </div>
          </v-stepper-window-item>

          <v-stepper-window-item :value="3">
            <div class="step-body">
              <p class="muted">{{ t('firstEventSetup.wizard.eventHint') }}</p>
              <template v-if="inProgressEventId">
                <v-alert type="info" density="compact" variant="tonal">
                  {{ t('firstEventSetup.wizard.eventAlreadyCreated', { name: eventName || '—' }) }}
                </v-alert>
                <v-btn color="primary" type="button" class="mt-3" @click="goNext">
                  {{ t('common.next') }}
                </v-btn>
              </template>
              <template v-else>
                <v-text-field v-model="eventName" :label="t('firstEventSetup.wizard.eventName')" required />
                <v-text-field
                  v-model="eventStart"
                  :label="t('firstEventSetup.wizard.eventStart')"
                  type="datetime-local"
                  required
                />
                <v-text-field
                  v-model="eventEnd"
                  :label="t('firstEventSetup.wizard.eventEnd')"
                  type="datetime-local"
                  required
                />
              </template>
            </div>
          </v-stepper-window-item>

          <v-stepper-window-item :value="4">
            <div class="step-body">
              <p class="muted">{{ t('firstEventSetup.wizard.stationHint') }}</p>
              <v-text-field v-model="stationName" :label="t('firstEventSetup.wizard.stationName')" required />
              <v-select
                v-model="selectedArticleIds"
                :items="articleSelectItems"
                item-title="title"
                item-value="value"
                :label="t('firstEventSetup.wizard.stationArticles')"
                multiple
                chips
                required
              />
              <v-select
                v-model="selectedWaiterIds"
                :items="waiterSelectItems"
                item-title="title"
                item-value="value"
                :label="t('firstEventSetup.wizard.eventWaiters')"
                multiple
                chips
                required
              />
            </div>
          </v-stepper-window-item>

          <v-stepper-window-item :value="5">
            <div class="step-body">
              <p class="muted">{{ t('firstEventSetup.wizard.layoutHint') }}</p>
              <v-text-field v-model="layoutName" :label="t('firstEventSetup.wizard.layoutName')" />
              <v-alert type="info" density="compact" variant="tonal" class="mb-3">
                {{ t('firstEventSetup.wizard.layoutSuggest', { count: layoutPreviewCells.length }) }}
              </v-alert>
              <ul class="layout-preview">
                <li v-for="(cell, idx) in layoutPreviewCells" :key="idx">
                  {{ cell.label }}
                </li>
              </ul>
            </div>
          </v-stepper-window-item>

          <v-stepper-window-item :value="6">
            <div class="step-body">
              <v-alert type="success" density="compact" variant="tonal" class="mb-3">
                {{ t('firstEventSetup.wizard.doneTitle') }}
              </v-alert>
              <p class="muted">{{ t('firstEventSetup.wizard.doneHint') }}</p>
              <p class="muted small">{{ devicesStatusLabel }}</p>
              <HostedPiCard v-if="inProgressEventId" :event-id="inProgressEventId" class="mt-3" />
              <div class="done-actions mt-4">
                <v-btn
                  v-if="inProgressEventId"
                  color="primary"
                  type="button"
                  @click="router.push({ name: 'events-detail', params: { id: String(inProgressEventId) } })"
                >
                  {{ t('firstEventSetup.wizard.openEvent') }}
                </v-btn>
                <v-btn variant="outlined" type="button" @click="router.push({ name: 'dashboard' })">
                  {{ t('firstEventSetup.wizard.backToDashboard') }}
                </v-btn>
              </div>
            </div>
          </v-stepper-window-item>
        </v-stepper-window>
      </v-stepper>

      <div v-if="currentStep !== 'done'" class="wizard-footer">
        <v-btn
          variant="outlined"
          type="button"
          :disabled="stepIndex <= 1 || saving"
          @click="stepIndex -= 1"
        >
          {{ t('common.back') }}
        </v-btn>
        <v-btn
          color="primary"
          type="button"
          :loading="saving"
          :disabled="saving"
          @click="onPrimary"
        >
          {{ primaryLabel }}
        </v-btn>
      </div>
      <p v-if="stepError" class="error footer-error">{{ stepError }}</p>
    </v-card>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { apiJson } from '@/api'
import type { ArticleRead, EventConfigurationRead, EventRead, WaiterRead } from '@/types/api'
import {
  FIRST_EVENT_SETUP_STEPS,
  resolveFirstEventSetupStep,
  suggestLayoutCells,
  suggestLayoutGrid,
  type FirstEventSetupStepId,
} from '@/utils/firstEventSetup'
import HostedPiCard from './HostedPiCard.vue'

const props = defineProps<{
  activeOrganisationId?: number | null
}>()

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const organisationId = computed(() => {
  const fromQuery = Number(route.query.organisationId)
  if (Number.isFinite(fromQuery) && fromQuery > 0) return fromQuery
  return props.activeOrganisationId ?? null
})

const booting = ref(true)
const bootError = ref('')
const saving = ref(false)
const stepError = ref('')
const stepIndex = ref(1)

const sellableArticles = ref<ArticleRead[]>([])
const waiters = ref<WaiterRead[]>([])
const inProgressEventId = ref<number | null>(null)
const hasStationWithArticles = ref(false)
const hasEventWaiter = ref(false)
const hasAppLayout = ref(false)
const lendingCurrent = ref(0)
const lendingPlanned = ref(0)

const categoryName = ref('')
const articleRows = ref([{ name: '', price: 5 }])
const waiterName = ref('')
const waiterPin = ref('1234')
const eventName = ref('')
const eventStart = ref('')
const eventEnd = ref('')
const stationName = ref('Bar')
const selectedArticleIds = ref<number[]>([])
const selectedWaiterIds = ref<number[]>([])
const layoutName = ref('Default')

const currentStep = computed(
  () => FIRST_EVENT_SETUP_STEPS[stepIndex.value - 1] as FirstEventSetupStepId,
)
const canSkipMenu = computed(() => sellableArticles.value.length >= 1)
const canSkipWaiters = computed(() => waiters.value.length >= 1)

const articleSelectItems = computed(() =>
  sellableArticles.value.map((article) => ({
    title: article.label || article.name,
    value: article.id,
  })),
)
const waiterSelectItems = computed(() =>
  waiters.value.map((waiter) => ({
    title: waiter.name,
    value: waiter.id,
  })),
)

const layoutPreviewCells = computed(() => {
  const selected = sellableArticles.value.filter((article) =>
    selectedArticleIds.value.includes(article.id),
  )
  return suggestLayoutCells(selected.length ? selected : sellableArticles.value)
})

const devicesStatusLabel = computed(() => {
  if (lendingCurrent.value > 0) {
    return t('firstEventSetup.wizard.devicesCurrent', { count: lendingCurrent.value })
  }
  if (lendingPlanned.value > 0) {
    return t('firstEventSetup.wizard.devicesPlanned', { count: lendingPlanned.value })
  }
  return t('firstEventSetup.wizard.devicesNone')
})

const primaryLabel = computed(() => {
  if (currentStep.value === 'layout') return t('firstEventSetup.wizard.finish')
  if (
    (currentStep.value === 'menu' && canSkipMenu.value) ||
    (currentStep.value === 'waiters' && canSkipWaiters.value) ||
    (currentStep.value === 'event' && inProgressEventId.value != null)
  ) {
    return t('firstEventSetup.wizard.skipContinue')
  }
  return t('common.next')
})

function addArticleRow() {
  articleRows.value.push({ name: '', price: 5 })
}

function goNext() {
  if (stepIndex.value < FIRST_EVENT_SETUP_STEPS.length) {
    stepIndex.value += 1
  }
}

function toDatetimeLocalValue(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function defaultEventDates() {
  const start = new Date()
  start.setMinutes(0, 0, 0)
  start.setDate(start.getDate() + 7)
  const end = new Date(start)
  end.setHours(end.getHours() + 8)
  eventStart.value = toDatetimeLocalValue(start)
  eventEnd.value = toDatetimeLocalValue(end)
}

async function loadCatalog() {
  const orgId = organisationId.value
  if (!orgId) return
  const [articles, waiterRows] = await Promise.all([
    apiJson<ArticleRead[]>(`/articles/?organisation_id=${orgId}`),
    apiJson<WaiterRead[]>(`/waiters/?organisation_id=${orgId}`),
  ])
  sellableArticles.value = (articles || []).filter((article) => !article.is_addition && article.is_active !== false)
  waiters.value = waiterRows || []
  if (!selectedArticleIds.value.length) {
    selectedArticleIds.value = sellableArticles.value.map((article) => article.id)
  }
  if (!selectedWaiterIds.value.length) {
    selectedWaiterIds.value = waiters.value.map((waiter) => waiter.id)
  }
}

async function loadEventProgress(eventId: number) {
  const cfg = await apiJson<EventConfigurationRead>(`/events/${eventId}/configuration`)
  hasStationWithArticles.value = (cfg.stations || []).some(
    (station) => (station.article_ids || []).length > 0,
  )
  hasEventWaiter.value = (cfg.event_waiters || []).length > 0
  hasAppLayout.value = (cfg.app_layouts || []).length > 0
  if (hasStationWithArticles.value) {
    const station = cfg.stations.find((row) => (row.article_ids || []).length > 0)
    if (station) {
      stationName.value = station.name || stationName.value
      selectedArticleIds.value = [...(station.article_ids || [])]
    }
  }
  if (hasEventWaiter.value) {
    selectedWaiterIds.value = cfg.event_waiters
      .map((row) => row.source_waiter_id)
      .filter((id): id is number => typeof id === 'number')
  }
  try {
    const event = await apiJson<EventRead>(`/events/${eventId}`)
    eventName.value = event.name
  } catch {
    /* ignore */
  }
}

async function boot() {
  booting.value = true
  bootError.value = ''
  try {
    const orgId = organisationId.value
    if (!orgId) {
      bootError.value = t('common.noOrganisation')
      return
    }
    defaultEventDates()
    const summary = await apiJson<{
      first_event_setup: {
        available: boolean
        completed: boolean
        dismissed: boolean
        in_progress_event_id: number | null
      }
      lendings: { current: number; planned: number }
      catalog: { articles: number; waiters: number }
    }>(`/organisations/${orgId}/dashboard-summary`)
    lendingCurrent.value = summary.lendings.current
    lendingPlanned.value = summary.lendings.planned
    inProgressEventId.value = summary.first_event_setup.in_progress_event_id
    await loadCatalog()
    if (inProgressEventId.value) {
      await loadEventProgress(inProgressEventId.value)
    }
    const queryStep = route.query.step as FirstEventSetupStepId | undefined
    const resolved = resolveFirstEventSetupStep({
      sellableArticleCount: sellableArticles.value.length,
      waiterCount: waiters.value.length,
      inProgressEventId: inProgressEventId.value,
      hasStationWithArticles: hasStationWithArticles.value,
      hasEventWaiter: hasEventWaiter.value,
      hasAppLayout: hasAppLayout.value,
    })
    const step = queryStep && FIRST_EVENT_SETUP_STEPS.includes(queryStep) ? queryStep : resolved
    stepIndex.value = FIRST_EVENT_SETUP_STEPS.indexOf(step) + 1
  } catch (err: unknown) {
    bootError.value = err instanceof Error ? err.message : t('firstEventSetup.wizard.loadFailed')
  } finally {
    booting.value = false
  }
}

async function saveMenu() {
  const orgId = organisationId.value
  if (!orgId) return
  if (canSkipMenu.value) {
    goNext()
    return
  }
  const name = categoryName.value.trim()
  if (!name) throw new Error(t('firstEventSetup.wizard.categoryRequired'))
  const rows = articleRows.value.filter((row) => row.name.trim())
  if (!rows.length) throw new Error(t('firstEventSetup.wizard.articleRequired'))
  const category = await apiJson<{ id: number }>('/article-categories/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, organisation_id: orgId }),
  })
  for (const row of rows) {
    await apiJson('/articles/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: row.name.trim(),
        label: row.name.trim().slice(0, 21),
        price: Number(row.price) || 0,
        article_category_id: category.id,
        is_addition: false,
        is_active: true,
      }),
    })
  }
  await loadCatalog()
  goNext()
}

async function saveWaiters() {
  const orgId = organisationId.value
  if (!orgId) return
  if (canSkipWaiters.value) {
    goNext()
    return
  }
  const name = waiterName.value.trim()
  const pin = (waiterPin.value || '0000').trim()
  if (!name) throw new Error(t('firstEventSetup.wizard.waiterRequired'))
  await apiJson('/waiters/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, pin, organisation_id: orgId }),
  })
  await loadCatalog()
  goNext()
}

async function saveEvent() {
  const orgId = organisationId.value
  if (!orgId) return
  if (inProgressEventId.value) {
    goNext()
    return
  }
  const name = eventName.value.trim()
  if (!name) throw new Error(t('firstEventSetup.wizard.eventRequired'))
  if (!eventStart.value || !eventEnd.value) {
    throw new Error(t('firstEventSetup.wizard.eventDatesRequired'))
  }
  const created = await apiJson<EventRead>('/events/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name,
      status: 'config',
      start: new Date(eventStart.value).toISOString(),
      end: new Date(eventEnd.value).toISOString(),
      organisation_id: orgId,
      payment_mode: 'pay_later',
      payment_types: ['cash'],
      cash_registers_enabled: false,
      shift_settlement_enabled: false,
      vouchers_enabled: false,
      discounts_enabled: false,
      alternative_printers_enabled: false,
      kitchen_monitors_enabled: false,
      offer_payment_receipt: false,
      bluetooth_printing_enabled: false,
    }),
  })
  inProgressEventId.value = created.id
  await apiJson(`/organisations/${orgId}/first-event-setup`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ in_progress_event_id: created.id }),
  })
  goNext()
}

async function saveStationAndWaiters() {
  const eventId = inProgressEventId.value
  if (!eventId) throw new Error(t('firstEventSetup.wizard.eventMissing'))
  if (!stationName.value.trim()) throw new Error(t('firstEventSetup.wizard.stationRequired'))
  if (!selectedArticleIds.value.length) {
    throw new Error(t('firstEventSetup.wizard.stationArticlesRequired'))
  }
  if (!selectedWaiterIds.value.length) {
    throw new Error(t('firstEventSetup.wizard.eventWaitersRequired'))
  }
  const cfg = await apiJson<EventConfigurationRead>(`/events/${eventId}/configuration`)
  const selectedWaiters = waiters.value.filter((waiter) => selectedWaiterIds.value.includes(waiter.id))
  await apiJson(`/events/${eventId}/configuration`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      stations: [
        {
          uuid: cfg.stations[0]?.uuid ?? null,
          name: stationName.value.trim(),
          printer_appliance_id: null,
          article_ids: selectedArticleIds.value,
          printer_rules: [],
        },
      ],
      event_waiters: selectedWaiters.map((waiter) => ({
        uuid: null,
        name: waiter.name,
        pin: waiter.pin || '0000',
        source_waiter_id: waiter.id,
        subsidiary_code: null,
      })),
      app_layouts: (cfg.app_layouts || []).map((layout) => ({
        uuid: layout.uuid,
        name: layout.name,
        is_default: layout.is_default,
        grid_width: layout.grid_width,
        grid_height: layout.grid_height,
        cells: (layout.cells || []).map((cell) => ({
          row: cell.row,
          col: cell.col,
          label: cell.label,
          color: cell.color,
          article_ids: cell.article_ids || [],
          voucher_definition_uuid: cell.voucher_definition_uuid ?? null,
          voucher_definition_uuids: cell.voucher_definition_uuids || [],
        })),
      })),
      cash_registers: [],
      voucher_definitions: [],
      kitchen_monitors: [],
    }),
  })
  hasStationWithArticles.value = true
  hasEventWaiter.value = true
  goNext()
}

async function saveLayoutAndComplete() {
  const orgId = organisationId.value
  const eventId = inProgressEventId.value
  if (!orgId || !eventId) throw new Error(t('firstEventSetup.wizard.eventMissing'))
  const cfg = await apiJson<EventConfigurationRead>(`/events/${eventId}/configuration`)
  const articles = sellableArticles.value.filter((article) =>
    selectedArticleIds.value.includes(article.id),
  )
  const cells = suggestLayoutCells(articles.length ? articles : sellableArticles.value)
  const { width, height } = suggestLayoutGrid(cells.length)
  const layoutUuid = cfg.app_layouts[0]?.uuid || crypto.randomUUID()
  await apiJson(`/events/${eventId}/configuration`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      stations: (cfg.stations || []).map((station) => ({
        uuid: station.uuid,
        name: station.name,
        printer_appliance_id: station.printer_appliance_id,
        article_ids: station.article_ids || [],
        printer_rules: (station.printer_rules || []).map((rule) => ({
          sort_order: rule.sort_order,
          rule_type: rule.rule_type,
          table_from: rule.table_from,
          table_to: rule.table_to,
          pickup_prefix: rule.pickup_prefix,
          printer_appliance_id: rule.printer_appliance_id,
        })),
      })),
      event_waiters: (cfg.event_waiters || []).map((waiter) => ({
        uuid: waiter.uuid,
        name: waiter.name,
        pin: waiter.pin,
        source_waiter_id: waiter.source_waiter_id,
        subsidiary_code: waiter.subsidiary_code,
      })),
      app_layouts: [
        {
          uuid: layoutUuid,
          name: layoutName.value.trim() || 'Default',
          is_default: true,
          grid_width: width,
          grid_height: height,
          cells,
        },
      ],
      cash_registers: [],
      voucher_definitions: [],
      kitchen_monitors: [],
    }),
  })
  await apiJson(`/organisations/${orgId}/first-event-setup/complete`, { method: 'POST' })
  hasAppLayout.value = true
  goNext()
}

async function onPrimary() {
  saving.value = true
  stepError.value = ''
  try {
    if (currentStep.value === 'menu') await saveMenu()
    else if (currentStep.value === 'waiters') await saveWaiters()
    else if (currentStep.value === 'event') await saveEvent()
    else if (currentStep.value === 'station') await saveStationAndWaiters()
    else if (currentStep.value === 'layout') await saveLayoutAndComplete()
  } catch (err: unknown) {
    stepError.value = err instanceof Error ? err.message : t('firstEventSetup.wizard.saveFailed')
  } finally {
    saving.value = false
  }
}

watch(organisationId, () => {
  void boot()
})

onMounted(() => {
  void boot()
})
</script>

<style scoped>
.wizard-card {
  padding: 0.5rem 0 1rem;
}
.step-body {
  padding: 1rem 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.article-row {
  display: grid;
  grid-template-columns: 1fr 8rem auto;
  gap: 0.5rem;
  align-items: start;
}
.wizard-footer {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  padding: 0 1.25rem 0.5rem;
}
.footer-error {
  padding: 0 1.25rem 1rem;
}
.layout-preview {
  margin: 0;
  padding-left: 1.25rem;
}
.done-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}
.mt-3 {
  margin-top: 0.75rem;
}
.mt-4 {
  margin-top: 1rem;
}
.mb-3 {
  margin-bottom: 0.75rem;
}
</style>
