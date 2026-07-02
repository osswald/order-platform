<template>
  <section class="vq-page panel orderjutsu-import-wizard">
    <div class="vq-page-header panel-header">
      <div>
        <h1>{{ t('events.import.orderjutsu.title') }}</h1>
        <p>{{ t('events.import.orderjutsu.subtitle') }}</p>
      </div>
      <v-btn variant="outlined" type="button" @click="router.push({ name: 'events' })">
        {{ t('common.cancel') }}
      </v-btn>
    </div>

    <v-card variant="flat" border class="wizard-card">
      <input
        ref="fileInputRef"
        type="file"
        accept="application/json,.json"
        class="file-input"
        @change="onFileChange"
      />
      <v-stepper v-model="stepIndex" flat>
        <v-stepper-header>
          <template v-for="(step, idx) in visibleSteps" :key="step">
            <v-divider v-if="idx > 0" />
            <v-stepper-item
              :value="idx + 1"
              :title="t(`events.import.orderjutsu.steps.${step}`)"
              :complete="stepIndex > idx + 1"
            />
          </template>
        </v-stepper-header>

        <v-stepper-window v-model="stepIndex">
          <v-stepper-window-item v-for="(step, idx) in visibleSteps" :key="step" :value="idx + 1">
            <div class="step-body">
              <template v-if="step === 'upload'">
                <p class="muted">{{ t('events.import.orderjutsu.uploadHint') }}</p>
                <v-btn color="primary" type="button" :loading="previewLoading" @click="openFilePicker">
                  {{ t('events.import.orderjutsu.chooseFile') }}
                </v-btn>
                <p v-if="previewError" class="error">{{ previewError }}</p>
                <p v-if="preview" class="success">{{ t('events.import.orderjutsu.fileLoaded') }}</p>
              </template>

              <template v-else-if="step === 'event' && preview">
                <v-text-field v-model="eventName" :label="t('events.table.name')" required />
                <v-text-field v-model="eventStart" :label="t('events.table.start')" type="datetime-local" />
                <v-text-field v-model="eventEnd" :label="t('events.table.end')" type="datetime-local" />
                <v-alert v-if="!preview.event.currency_matches_org" type="warning" density="compact" class="mt-2">
                  {{ t('events.import.orderjutsu.currencyWarning', { currency: preview.event.currency }) }}
                </v-alert>
                <ul v-if="(preview.warnings || []).length" class="warning-list">
                  <li v-for="(w, wi) in preview.warnings || []" :key="wi">{{ w.message }}</li>
                </ul>
              </template>

              <template v-else-if="step === 'waiters' && preview">
                <div class="step-toolbar">
                  <v-btn size="small" variant="outlined" type="button" @click="setAllUnmatchedWaiters('event_only')">
                    {{ t('events.import.orderjutsu.allEventOnly') }}
                  </v-btn>
                  <v-btn size="small" variant="outlined" type="button" @click="setAllUnmatchedWaiters('create_org_waiter')">
                    {{ t('events.import.orderjutsu.allCreateOrgWaiters') }}
                  </v-btn>
                </div>
                <VqDataTable
                  :items="preview.cashiers"
                  item-value="index"
                  :headers="waiterHeaders"
                  hide-default-footer
                  class="vq-data-table nested"
                >
                  <template #item.match="{ item }">
                    <span v-if="item.match_kind === 'exact' && item.matched_waiter_name">{{ item.matched_waiter_name }}</span>
                    <span v-else class="muted">{{ t('events.import.orderjutsu.noMatchesFound') }}</span>
                  </template>
                  <template #item.action="{ item }">
                    <div class="action-cell">
                      <v-select
                        :model-value="waiterActions[item.index]?.action"
                        :items="waiterActionOptions"
                        item-title="label"
                        item-value="value"
                        density="compact"
                        hide-details
                        @update:model-value="(v) => updateWaiterAction(item.index, v as WaiterAction, item)"
                      />
                      <v-select
                        v-if="waiterActions[item.index]?.action === 'link_existing'"
                        :model-value="waiterActions[item.index]?.waiterId"
                        :items="waiterSelectOptions"
                        item-title="label"
                        item-value="value"
                        :label="t('events.import.orderjutsu.selectExistingWaiter')"
                        :loading="catalogLoading"
                        density="compact"
                        hide-details
                        clearable
                        @update:model-value="(v) => updateWaiterLink(item.index, v as number | null)"
                      />
                    </div>
                  </template>
                </VqDataTable>
              </template>

              <template v-else-if="step === 'articles' && preview">
                <div class="step-toolbar">
                  <v-btn size="small" variant="outlined" type="button" @click="setAllUnmatchedArticles('create_new')">
                    {{ t('events.import.orderjutsu.createAllUnmatched') }}
                  </v-btn>
                </div>
                <VqDataTable
                  :items="sellableProducts"
                  item-value="ref"
                  :headers="articleHeaders"
                  hide-default-footer
                  class="vq-data-table nested"
                >
                  <template #item.action="{ item }">
                    <div class="action-cell">
                      <v-select
                        :model-value="articleActions[item.ref]?.action"
                        :items="articleActionOptions"
                        item-title="label"
                        item-value="value"
                        density="compact"
                        hide-details
                        @update:model-value="(v) => updateArticleAction(item.ref, v as ArticleAction, item)"
                      />
                      <v-select
                        v-if="articleActions[item.ref]?.action === 'link_existing'"
                        :model-value="articleActions[item.ref]?.articleId"
                        :items="articleOptionsForProduct(item)"
                        item-title="label"
                        item-value="value"
                        :label="t('events.import.orderjutsu.selectExistingArticle')"
                        :loading="catalogLoading"
                        density="compact"
                        hide-details
                        clearable
                        @update:model-value="(v) => updateArticleLink(item.ref, v as number | null)"
                      />
                    </div>
                  </template>
                  <template #item.match="{ item }">
                    <span
                      v-if="item.match_kind === 'exact' || item.match_kind === 'import_number'"
                      :class="{ warn: articlePriceDiffers(item) }"
                    >
                      {{ formatArticleMatch(item) }}
                    </span>
                    <span v-else-if="item.match_kind === 'ambiguous'" class="warn">{{ t('events.import.orderjutsu.ambiguous') }}</span>
                    <span v-else class="muted">{{ t('events.import.orderjutsu.noMatch') }}</span>
                  </template>
                </VqDataTable>
              </template>

              <template v-else-if="step === 'categories'">
                <v-select
                  v-model="defaultCategoryId"
                  :items="categoryOptions"
                  item-title="label"
                  item-value="value"
                  :label="t('events.import.orderjutsu.defaultCategory')"
                  :loading="categoriesLoading"
                  required
                />
              </template>

              <template v-else-if="step === 'additions' && preview">
                <VqDataTable
                  :items="extraRows"
                  item-value="row_key"
                  :headers="extraHeaders"
                  hide-default-footer
                  class="vq-data-table nested"
                />
              </template>

              <template v-else-if="step === 'ingredients' && preview">
                <v-checkbox
                  v-if="preview.will_enable_ingredients"
                  v-model="enableIngredients"
                  :label="t('events.import.orderjutsu.enableIngredients')"
                  hide-details
                />
                <VqDataTable
                  :items="preview.ingredient_matches"
                  item-value="ref"
                  :headers="ingredientHeaders"
                  hide-default-footer
                  class="vq-data-table nested"
                />
                <h3 class="mt-4">{{ t('events.import.orderjutsu.recipes') }}</h3>
                <VqDataTable
                  :items="preview.recipe_rows"
                  :headers="recipeHeaders"
                  hide-default-footer
                  class="vq-data-table nested"
                />
              </template>

              <template v-else-if="step === 'stations' && preview">
                <VqDataTable
                  :items="stationRows"
                  item-value="index"
                  :headers="stationHeaders"
                  hide-default-footer
                  class="vq-data-table nested"
                />
              </template>

              <template v-else-if="step === 'stock' && preview">
                <v-checkbox v-model="importStock" :label="t('events.import.orderjutsu.importStock')" hide-details />
                <VqDataTable
                  :items="preview.stock_candidates"
                  item-value="ref"
                  :headers="stockHeaders"
                  hide-default-footer
                  class="vq-data-table nested"
                />
              </template>

              <template v-else-if="step === 'layouts' && preview">
                <VqDataTable
                  :items="layoutRows"
                  item-value="name"
                  :headers="layoutHeaders"
                  hide-default-footer
                  class="vq-data-table nested"
                />
              </template>

              <template v-else-if="step === 'vouchers' && preview">
                <v-checkbox v-model="importVouchers" :label="t('events.import.orderjutsu.importVouchers')" hide-details />
                <VqDataTable
                  :items="preview.vouchers"
                  item-value="ref"
                  :headers="voucherHeaders"
                  hide-default-footer
                  class="vq-data-table nested"
                />
              </template>

              <template v-else-if="step === 'review' && preview">
                <ul class="review-summary">
                  <li>{{ t('events.import.orderjutsu.summaryEvent', { name: eventName }) }}</li>
                  <li>{{ t('events.import.orderjutsu.summaryArticles', { count: sellableProducts.length }) }}</li>
                  <li>{{ t('events.import.orderjutsu.summaryWaiters', { count: preview.cashiers.length }) }}</li>
                  <li>{{ t('events.import.orderjutsu.summaryStations', { count: preview.stations.length }) }}</li>
                  <li v-if="preview.has_ingredients">{{ t('events.import.orderjutsu.summaryRecipes', { count: preview.recipe_rows.length }) }}</li>
                </ul>
                <p v-if="commitError" class="error">{{ commitError }}</p>
              </template>
            </div>
          </v-stepper-window-item>
        </v-stepper-window>
      </v-stepper>

      <div class="wizard-actions">
        <v-btn variant="outlined" type="button" :disabled="stepIndex <= 1 || commitLoading" @click="stepIndex -= 1">
          {{ t('common.back') }}
        </v-btn>
        <v-spacer />
        <v-btn
          v-if="currentStep !== 'review'"
          color="primary"
          type="button"
          :disabled="!canNext"
          @click="stepIndex += 1"
        >
          {{ t('common.next') }}
        </v-btn>
        <v-btn
          v-else
          color="primary"
          type="button"
          :loading="commitLoading"
          :disabled="!canCommit"
          @click="onCommit"
        >
          {{ t('events.import.orderjutsu.import') }}
        </v-btn>
      </div>
    </v-card>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import VqDataTable from './VqDataTable.vue'
import { apiJson } from '@/api'
import { loadOrgCatalog } from '@/composables/useOrgCatalog'
import { formatPriceWithCurrency } from '@/utils/localeFormat'
import {
  useOrderjutsuImport,
  type ArticleAction,
  type OrderjutsuImportPreview,
  type WaiterAction,
  type WizardStepId,
} from '@/composables/useOrderjutsuImport'
import type { ArticleRead, WaiterRead } from '@/types/api'
import type { DataTableHeader } from '@/types/vuetify'
import type { SelectOption } from '@/types/ui'

const props = defineProps<{
  activeOrganisationId: number | null
}>()

const { t, locale } = useI18n()
const router = useRouter()
const stepIndex = ref(1)
const fileInputRef = ref<HTMLInputElement | null>(null)
const categoriesLoading = ref(false)
const catalogLoading = ref(false)
const categoryOptions = ref<SelectOption<number>[]>([])
const orgArticles = ref<ArticleRead[]>([])
const orgWaiters = ref<WaiterRead[]>([])

const {
  preview,
  previewLoading,
  previewError,
  commitLoading,
  commitError,
  eventName,
  eventStart,
  eventEnd,
  enableIngredients,
  defaultCategoryId,
  importStock,
  importVouchers,
  articleActions,
  waiterActions,
  visibleSteps,
  loadPreview,
  commitImport,
  setAllUnmatchedArticles,
  setAllUnmatchedWaiters,
} = useOrderjutsuImport(() => props.activeOrganisationId)

const currentStep = computed((): WizardStepId => visibleSteps.value[stepIndex.value - 1] ?? 'upload')

const sellableProducts = computed(() => (preview.value?.products || []).filter((p) => !p.ingredient_only))

const productsByRef = computed(() => {
  const map = new Map<number, PreviewProduct>()
  for (const product of preview.value?.products || []) {
    map.set(product.ref, product)
  }
  return map
})

function productDisplayName(ref: number): string {
  const product = productsByRef.value.get(ref)
  if (!product) return String(ref)
  return product.bon_text?.trim() || product.label?.trim() || String(ref)
}

const extraRows = computed(() =>
  (preview.value?.product_extras || []).map((row) => ({
    ...row,
    row_key: `${row.product_ref}-${row.extra_ref}`,
    product_bon_text: productDisplayName(row.product_ref),
    extra_bon_text: productDisplayName(row.extra_ref),
  })),
)

const stationRows = computed(() =>
  (preview.value?.stations || []).map((st) => ({
    ...st,
    article_count: (st.product_refs || []).length,
    printer_hint: st.printer_loc || t('common.emDash'),
  })),
)

const layoutRows = computed(() =>
  (preview.value?.layouts || []).map((lo) => ({
    ...lo,
    grid_label: `${lo.grid_width}×${lo.grid_height}`,
  })),
)

const waiterActionOptions = computed(() => [
  { value: 'link_existing', label: t('events.import.orderjutsu.actionLinkExisting') },
  { value: 'create_org_waiter', label: t('events.import.orderjutsu.actionCreateOrgWaiter') },
  { value: 'event_only', label: t('events.import.orderjutsu.actionEventOnly') },
  { value: 'skip', label: t('events.import.orderjutsu.actionSkip') },
])

const articleActionOptions = computed(() => [
  { value: 'link_existing', label: t('events.import.orderjutsu.actionLinkExisting') },
  { value: 'create_new', label: t('events.import.orderjutsu.actionCreateNew') },
  { value: 'skip', label: t('events.import.orderjutsu.actionSkip') },
])

const waiterHeaders = computed((): DataTableHeader[] => [
  { title: t('events.import.orderjutsu.waiter'), key: 'label' },
  { title: 'PIN', key: 'pin' },
  { title: t('events.import.orderjutsu.match'), key: 'match', sortable: false },
  { title: t('events.import.orderjutsu.action'), key: 'action', sortable: false, width: '18rem' },
])

type PreviewCashier = OrderjutsuImportPreview['cashiers'][number]
type PreviewProduct = OrderjutsuImportPreview['products'][number]

const waiterSelectOptions = computed((): SelectOption<number>[] =>
  orgWaiters.value.map((waiter) => ({ value: waiter.id, label: waiter.name })),
)

function waiterActionsComplete(): boolean {
  return (preview.value?.cashiers || []).every((cashier) => {
    const row = waiterActions.value[cashier.index]
    if (!row) return false
    if (row.action === 'link_existing') return row.waiterId != null
    return true
  })
}

const articleHeaders = computed((): DataTableHeader[] => [
  { title: t('events.import.orderjutsu.bonText'), key: 'bon_text' },
  { title: t('events.import.orderjutsu.price'), key: 'price' },
  { title: t('events.import.orderjutsu.match'), key: 'match', sortable: false },
  { title: t('events.import.orderjutsu.action'), key: 'action', sortable: false, width: '18rem' },
])

const articleSelectOptions = computed((): SelectOption<number>[] =>
  orgArticles.value.map((article) => ({
    value: article.id,
    label: formatArticleOptionLabel(article.name, article.price),
  })),
)

const importCurrency = computed(() => preview.value?.event.currency ?? 'CHF')

function formatArticleOptionLabel(name: string, price: number): string {
  return `${name} (${formatPriceWithCurrency(price, importCurrency.value, locale.value)})`
}

function formatArticleMatch(item: PreviewProduct): string {
  if (!item.matched_article_name) return ''
  if (item.matched_article_price == null) return item.matched_article_name
  return formatArticleOptionLabel(item.matched_article_name, item.matched_article_price)
}

function articlePriceDiffers(item: PreviewProduct): boolean {
  if (item.matched_article_price == null) return false
  return Math.abs(item.matched_article_price - item.price) > 0.001
}

function articleOptionsForProduct(item: PreviewProduct): SelectOption<number>[] {
  const options = articleSelectOptions.value
  if (item.match_kind === 'ambiguous' && item.ambiguous_article_ids?.length) {
    const ids = new Set(item.ambiguous_article_ids)
    const candidates = options.filter((option) => ids.has(option.value))
    if (candidates.length) return candidates
  }
  return options
}

function articleActionsComplete(): boolean {
  return sellableProducts.value.every((product) => {
    const row = articleActions.value[product.ref]
    if (!row) return false
    if (row.action === 'link_existing') return row.articleId != null
    return true
  })
}

const extraHeaders = computed((): DataTableHeader[] => [
  { title: t('events.import.orderjutsu.product'), key: 'product_bon_text' },
  { title: t('events.import.orderjutsu.addition'), key: 'extra_bon_text' },
])

const ingredientHeaders = computed((): DataTableHeader[] => [
  { title: t('events.import.orderjutsu.bonText'), key: 'bon_text' },
  { title: t('events.import.orderjutsu.match'), key: 'matched_ingredient_name' },
])

const recipeHeaders = computed((): DataTableHeader[] => [
  { title: t('events.import.orderjutsu.product'), key: 'product_bon_text' },
  { title: t('events.import.orderjutsu.ingredient'), key: 'ingredient_bon_text' },
  { title: t('events.import.orderjutsu.amount'), key: 'amount' },
])

const stationHeaders = computed((): DataTableHeader[] => [
  { title: t('events.import.orderjutsu.station'), key: 'label' },
  { title: t('events.import.orderjutsu.articles'), key: 'article_count' },
  { title: t('events.import.orderjutsu.printerHint'), key: 'printer_hint', sortable: false },
])

const stockHeaders = computed((): DataTableHeader[] => [
  { title: t('events.import.orderjutsu.bonText'), key: 'bon_text' },
  { title: t('events.import.orderjutsu.kind'), key: 'kind' },
  { title: t('events.import.orderjutsu.stock'), key: 'stock' },
])

const layoutHeaders = computed((): DataTableHeader[] => [
  { title: t('events.import.orderjutsu.layout'), key: 'name' },
  { title: t('events.import.orderjutsu.grid'), key: 'grid_label' },
  { title: t('events.import.orderjutsu.cells'), key: 'cell_count' },
])

const voucherHeaders = computed((): DataTableHeader[] => [
  { title: t('events.import.orderjutsu.bonText'), key: 'label' },
  { title: t('events.import.orderjutsu.price'), key: 'price' },
])

const canNext = computed(() => {
  if (currentStep.value === 'upload') return !!preview.value
  if (currentStep.value === 'waiters') return waiterActionsComplete()
  if (currentStep.value === 'articles') return articleActionsComplete()
  if (currentStep.value === 'categories') return defaultCategoryId.value != null
  if (currentStep.value === 'ingredients' && preview.value?.will_enable_ingredients) return enableIngredients.value
  return true
})

const canCommit = computed(
  () =>
    !!preview.value &&
    defaultCategoryId.value != null &&
    !!eventName.value.trim() &&
    waiterActionsComplete() &&
    articleActionsComplete(),
)

function updateArticleAction(
  ref: number,
  action: ArticleAction,
  product?: PreviewProduct,
) {
  let articleId: number | null = null
  if (action === 'link_existing') {
    articleId =
      product?.matched_article_id ??
      articleActions.value[ref]?.articleId ??
      null
  }
  articleActions.value[ref] = { action, articleId }
}

function updateArticleLink(ref: number, articleId: number | null) {
  articleActions.value[ref] = { action: 'link_existing', articleId }
}

function updateWaiterAction(
  index: number,
  action: WaiterAction,
  cashier?: PreviewCashier,
) {
  let waiterId: number | null = null
  if (action === 'link_existing') {
    waiterId =
      cashier?.matched_waiter_id ??
      waiterActions.value[index]?.waiterId ??
      null
  }
  waiterActions.value[index] = { action, waiterId }
}

function updateWaiterLink(index: number, waiterId: number | null) {
  waiterActions.value[index] = { action: 'link_existing', waiterId }
}

function openFilePicker() {
  fileInputRef.value?.click()
}

async function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  try {
    await loadPreview(file)
    await loadOrgCatalogData()
    if (visibleSteps.value.length > 1) stepIndex.value = 2
  } catch {
    /* previewError set in composable */
  }
}

async function loadOrgCatalogData() {
  if (!props.activeOrganisationId) return
  catalogLoading.value = true
  try {
    const { articles, waiters } = await loadOrgCatalog(props.activeOrganisationId)
    orgArticles.value = articles.filter((article) => article.is_active && !article.is_addition)
    orgWaiters.value = waiters
  } finally {
    catalogLoading.value = false
  }
}

async function loadCategories() {
  if (!props.activeOrganisationId) return
  categoriesLoading.value = true
  try {
    const rows = await apiJson<Array<{ id: number; name: string }>>(
      `/article-categories/?organisation_id=${props.activeOrganisationId}`,
    )
    categoryOptions.value = rows.map((row) => ({ value: row.id, label: row.name }))
    if (!defaultCategoryId.value && categoryOptions.value.length) {
      defaultCategoryId.value = categoryOptions.value[0].value
    }
  } finally {
    categoriesLoading.value = false
  }
}

async function onCommit() {
  try {
    const result = await commitImport()
    await router.push({ name: 'events', params: { id: String(result.event_id) } })
  } catch {
    /* commitError set */
  }
}

watch(
  () => props.activeOrganisationId,
  () => {
    loadCategories()
    if (preview.value) void loadOrgCatalogData()
  },
  { immediate: true },
)

onMounted(() => {
  loadCategories()
})
</script>

<style scoped>
.orderjutsu-import-wizard .wizard-card {
  padding: 1rem;
}

.step-body {
  padding: 1rem 0;
  min-height: 12rem;
}

.step-toolbar {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
  flex-wrap: wrap;
}

.action-cell {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  min-width: 14rem;
}

.wizard-actions {
  display: flex;
  gap: 0.5rem;
  padding: 1rem 0 0;
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.file-input {
  display: none;
}

.warning-list {
  margin: 0.75rem 0 0;
  padding-left: 1.25rem;
  color: rgb(var(--v-theme-warning));
}

.review-summary {
  margin: 0;
  padding-left: 1.25rem;
}

.warn {
  color: rgb(var(--v-theme-warning));
}
</style>
