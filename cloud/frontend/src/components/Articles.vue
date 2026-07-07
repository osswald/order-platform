<template>
  <ListDetailLayout
    :title="$t('articles.title')"
    :subtitle="$t('articles.subtitle')"
    :createLabel="$t('articles.createLabel')"
    :showCreate="canCreateArticles"
    :showDetail="showDetail"
    @open-create="openCreateForm"
  >
    <template #detail>
      <h2>{{ editMode ? $t('articles.editTitle') : $t('articles.newTitle') }}</h2>
      <p class="form-required-legend"><span class="vq-asterisk">*</span> {{ $t('common.requiredLegend') }}</p>

      <v-form ref="formRef" @submit.prevent="saveArticle">
      <div class="form-field">
        <v-text-field
          v-model="form.name"
          :label="$t('common.name')"
          :placeholder="$t('articles.namePlaceholder')"
          hide-details="auto"
          required
          :rules="[rules.required]"
        />
      </div>

      <div class="form-field">
        <v-text-field
          v-model="form.label"
          :label="$t('common.label')"
          maxlength="22"
          :placeholder="$t('articles.labelPlaceholder')"
          hide-details="auto"
          required
          :rules="labelRules"
        />
        <small>{{ $t('articles.labelCharCount', { count: form.label.length }) }}</small>
      </div>

      <div class="form-field">
        <v-text-field
          v-model="form.importArticleNumber"
          :label="$t('articles.importArticleNumber')"
          :placeholder="$t('articles.importArticleNumberPlaceholder')"
          hide-details="auto"
        />
      </div>

      <div class="form-field">
        <v-textarea
          v-model="form.description"
          :label="$t('common.description')"
          rows="4"
          auto-grow
          :placeholder="$t('articles.descriptionPlaceholder')"
          hide-details="auto"
        />
      </div>

      <div class="field-row">
        <div class="form-field">
          <v-text-field v-model="form.unit" :label="$t('common.unit')" :placeholder="$t('articles.unitPlaceholder')" hide-details="auto" />
        </div>
      </div>

      <div v-if="showTaxCodeField" class="form-field">
        <v-select
          v-model="form.taxCodeId"
          :items="taxCodeOptions"
          item-title="title"
          item-value="value"
          :label="$t('articles.taxCode')"
          :loading="taxCodesLoading"
          hide-details="auto"
          required
          :rules="taxCodeRules"
        />
      </div>

      <div class="stock-field">
        <v-checkbox v-model="form.isAddition" :label="$t('articles.isAddition')" hide-details density="compact" />
      </div>
      <div class="stock-field">
        <v-checkbox v-model="form.isActive" :label="$t('articles.isActive')" hide-details density="compact" />
      </div>
      <small v-if="form.isAddition" class="muted block-hint">
        {{ $t('articles.additionPriceHint') }}
      </small>

      <div class="field-row">
        <div class="form-field">
          <v-text-field
            v-model.number="form.price"
            type="number"
            step="0.01"
            :min="form.isAddition ? undefined : 0"
            :label="$t('common.price')"
            :prefix="formCurrency"
            hide-details="auto"
            required
            :rules="priceRules"
          />
        </div>
        <div class="form-field">
          <v-select
            v-model="form.articleCategoryId"
            :items="categoryOptions"
            item-title="label"
            item-value="value"
            :label="$t('common.category')"
            :placeholder="$t('articles.selectCategory')"
            hide-details="auto"
            required
            :rules="[rules.required]"
          />
        </div>
      </div>

      <div v-if="showAccountingAccountField" class="form-field">
        <v-select
          v-model="form.accountingAccountId"
          :items="accountingAccountOptions"
          item-title="title"
          item-value="value"
          :label="$t('articles.accountingAccount')"
          :placeholder="$t('common.optional')"
          :loading="accountingAccountsLoading"
          hide-details="auto"
          clearable
        />
      </div>

      <div v-if="editMode && activeId && !form.isAddition" class="additions-section">
        <h3>{{ $t('articles.additionsTitle') }}</h3>
        <p class="muted small">{{ $t('articles.additionsHint') }}</p>
        <p class="muted small">{{ $t('articles.preselectedHint') }}</p>
        <div class="form-field">
          <v-select
            v-model="additionPickIds"
            :items="additionOptions"
            item-title="label"
            item-value="value"
            :label="$t('articles.addAddition')"
            :placeholder="$t('articles.selectAdditions')"
            multiple
            chips
            closable-chips
            hide-details="auto"
            @update:model-value="onAdditionPick"
          />
        </div>
        <VqDataTable
          :headers="additionsHeaders"
          :items="additionsLocal"
          item-value="addition_article_id"
          class="vq-data-table list-table nested"
          hide-default-footer
        >
          <template #item.price="{ item }">{{ formatPrice(item.price, formCurrency) }}</template>
          <template #item.preselected="{ item }">
            <v-checkbox
              :model-value="item.preselected"
              hide-details
              density="compact"
              @update:model-value="(v: boolean | null) => (item.preselected = v === true)"
            />
          </template>
          <template #item.actions="{ item }">
            <v-btn
              icon="mdi-delete"
              variant="text"
              color="error"
              size="small"
              type="button"
              @click="removeAdditionLink(item)"
            />
          </template>
          <template #no-data>{{ $t('articles.noAdditionsLinked') }}</template>
        </VqDataTable>
        <v-btn
          color="primary"
          type="button"
          style="margin-top: 0.75rem"
          :disabled="!activeId"
          @click="saveAdditions"
        >
          {{ $t('articles.saveAdditions') }}
        </v-btn>
        <p v-if="additionsMessage" :class="additionsMessageType">{{ additionsMessage }}</p>
      </div>

      <div v-if="showIngredientsSection" class="ingredients-section">
        <h3>{{ $t('articles.ingredientsTitle') }}</h3>
        <p class="muted small">{{ $t('articles.ingredientsHint') }}</p>
        <div class="form-field">
          <v-select
            v-model="ingredientPickIds"
            :items="ingredientOptions"
            item-title="label"
            item-value="value"
            :label="$t('articles.addIngredient')"
            :placeholder="$t('articles.selectIngredients')"
            multiple
            chips
            closable-chips
            hide-details="auto"
            @update:model-value="onIngredientPick"
          />
        </div>
        <VqDataTable
          :headers="ingredientsHeaders"
          :items="ingredientsLocal"
          item-value="ingredient_id"
          class="vq-data-table list-table nested"
          hide-default-footer
        >
          <template #item.unit="{ item }">
            {{ item.unit || $t('common.emDash') }}
          </template>
          <template #item.amount="{ item }">
            <v-text-field
              v-model.number="item.amount"
              type="number"
              min="0.001"
              step="any"
              hide-details
              density="compact"
            />
          </template>
          <template #item.actions="{ item }">
            <v-btn
              icon="mdi-delete"
              variant="text"
              color="error"
              size="small"
              type="button"
              @click="removeIngredientLink(item)"
            />
          </template>
          <template #no-data>{{ $t('articles.noIngredientsLinked') }}</template>
        </VqDataTable>
        <v-btn
          color="primary"
          type="button"
          style="margin-top: 0.75rem"
          :disabled="!activeId"
          @click="saveIngredients"
        >
          {{ $t('articles.saveIngredients') }}
        </v-btn>
        <p v-if="ingredientsMessage" :class="ingredientsMessageType">{{ ingredientsMessage }}</p>
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
        <h2>{{ $t('articles.allTitle') }}</h2>
        <span>{{ $t('common.entriesCount', { filtered: filteredArticles.length, total: articlesInActiveOrganisation.length }) }}</span>
      </div>
      <div class="list-controls">
        <div class="search-field">
          <v-text-field
            v-model="searchQuery"
            :label="$t('common.search')"
            prepend-inner-icon="mdi-magnify"
            :placeholder="$t('articles.searchPlaceholder')"
            hide-details
            density="compact"
          />
        </div>
        <div class="filter-field">
          <v-select
            v-model="typeFilter"
            :items="typeFilterOptions"
            item-title="label"
            item-value="value"
            :label="$t('common.type')"
            hide-details
            density="compact"
          />
        </div>
        <div class="filter-field">
          <v-select
            v-model="statusFilter"
            :items="statusFilterOptions"
            item-title="label"
            item-value="value"
            :label="$t('articles.filterStatus')"
            hide-details
            density="compact"
          />
        </div>
        <div class="filter-field">
          <v-select
            v-model="categoryFilter"
            :items="categoryFilterOptions"
            item-title="label"
            item-value="value"
            :label="$t('common.category')"
            :placeholder="$t('articles.allCategories')"
            hide-details
            density="compact"
          />
        </div>
      </div>

      <VqDataTable
        v-model:page="currentPage"
        :headers="tableHeaders"
        :items="filteredArticles"
        :items-per-page="pageSize"
        item-value="id"
        class="vq-data-table list-table"
        hover
        @click:row="onArticleRowClick"
      >
        <template #item.is_addition="{ item }">
          <v-chip :color="item.is_addition ? 'warning' : undefined" size="small" variant="tonal">
            {{ item.is_addition ? $t('articles.typeAddition') : $t('articles.typeArticle') }}
          </v-chip>
        </template>
        <template #item.is_active="{ item }">
          {{ item.is_active ? $t('common.yes') : $t('common.no') }}
        </template>
        <template #item.price="{ item }">{{ formatPrice(item.price, item.organisation_currency) }}</template>
        <template #item.actions="{ item }">
          <v-btn color="error" variant="outlined" size="small" @click.stop="deleteArticle(item.id)">
            {{ $t('common.delete') }}
          </v-btn>
        </template>
        <template #no-data>{{ $t('articles.noData') }}</template>
      </VqDataTable>
    </template>
  </ListDetailLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, inject } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import ListDetailLayout from './ListDetailLayout.vue'
import { apiJson } from '../api'
import { useListDetailRouting } from '../composables/useListDetailRouting'
import { useClientPagination } from '../composables/useClientPagination'
import { invalidateOrgCatalog } from '../composables/useOrgCatalog'
import { matchesActiveOrganisation, organisationAccountsEnabled, organisationIngredientsEnabled } from '../utils/orgScope'
import { filterArticleList } from '../utils/articleListFilters'
import { articleListHeaders } from '../utils/orgScopedListTableHeaders'
import { rules, validateForm } from '../utils/formRules.js'
import { formatPriceWithCurrency } from '../utils/localeFormat.js'
import { useTaxCodes } from '../composables/useTaxCodes'
import { useAccountingAccounts } from '../composables/useAccountingAccounts'
import { SESSION_CONTEXT_KEY } from '../sessionContext'
import VqDataTable from './VqDataTable.vue'
import type { ArticleRead, ArticleCategoryRead, ArticleAdditionsRead, ArticleIngredientsRead, IngredientRead } from '@/types/api'
import { isApiError, getErrorMessage } from '@/types/api'
import type { AccessibleOrganisation, AdditionLinkLocal, IngredientLinkLocal, ArticleForm, SessionContext } from '@/types/ui'
import type { DataTableHeader } from '@/types/vuetify'

const { t, locale } = useI18n()

const props = withDefaults(
  defineProps<{
    activeOrganisationId?: number | null
  }>(),
  {
    activeOrganisationId: null,
  },
)

const route = useRoute()
const {
  isCreateMode,
  editMode,
  showDetail,
  routeEntityId,
  goToList,
  goToCreate,
  goToDetail,
} = useListDetailRouting('articles')

const articles = ref<ArticleRead[]>([])
const categories = ref<ArticleCategoryRead[]>([])
const sessionContext = inject<SessionContext | null>(SESSION_CONTEXT_KEY, null)
const organisationsList = computed(
  () => (sessionContext?.accessibleOrganisations?.value ?? []) as AccessibleOrganisation[],
)
const formCurrency = ref('EUR')
const activeId = computed(() => routeEntityId.value)
const message = ref('')
const messageType = ref('')
const searchQuery = ref('')
const categoryFilter = ref<number | null>(null)
const typeFilter = ref<'articles' | 'additions' | 'all'>('articles')
const statusFilter = ref<'active' | 'inactive' | 'all'>('active')
const additionsLocal = ref<AdditionLinkLocal[]>([])
const additionPickIds = ref<number[]>([])
const additionsMessage = ref('')
const additionsMessageType = ref('')
const ingredientsLocal = ref<IngredientLinkLocal[]>([])
const ingredientCatalog = ref<IngredientRead[]>([])
const ingredientPickIds = ref<number[]>([])
const ingredientsMessage = ref('')
const ingredientsMessageType = ref('')

const tableHeaders = computed((): DataTableHeader[] => articleListHeaders(t))

const additionsHeaders = computed((): DataTableHeader[] => [
  { title: t('articles.additionColumn'), key: 'name' },
  { title: t('common.price'), key: 'price', sortable: false },
  { title: t('articles.preselectedColumn'), key: 'preselected', sortable: false, align: 'center', width: 120 },
  { title: '', key: 'actions', sortable: false, align: 'end', width: 56 },
])

const ingredientsHeaders = computed((): DataTableHeader[] => [
  { title: t('articles.ingredientColumn'), key: 'name' },
  { title: t('common.unit'), key: 'unit', sortable: false },
  { title: t('articles.amountColumn'), key: 'amount', sortable: false, width: 120 },
  { title: '', key: 'actions', sortable: false, align: 'end', width: 56 },
])

const emptyForm = (): ArticleForm => ({
  name: '',
  label: '',
  importArticleNumber: '',
  description: '',
  unit: '',
  accountingAccountId: null,
  taxCodeId: null,
  price: 0,
  isAddition: false,
  isActive: true,
  articleCategoryId: null,
})

const typeFilterOptions = computed(() => [
  { value: 'articles' as const, label: t('articles.typeArticle') },
  { value: 'additions' as const, label: t('articles.typeAddition') },
  { value: 'all' as const, label: t('articles.typeAll') },
])

const statusFilterOptions = computed(() => [
  { value: 'active' as const, label: t('articles.statusActive') },
  { value: 'inactive' as const, label: t('articles.statusInactive') },
  { value: 'all' as const, label: t('articles.statusAll') },
])

const form = ref<ArticleForm>(emptyForm())

const activeOrganisation = computed(() => {
  if (props.activeOrganisationId == null) return null
  return organisationsList.value.find(
    (org) => Number(org.id) === Number(props.activeOrganisationId),
  ) ?? null
})

const showTaxCodeField = computed(() => Boolean(activeOrganisation.value?.vat_liable))
const showAccountingAccountField = computed(() =>
  organisationAccountsEnabled(organisationsList.value, props.activeOrganisationId),
)

const showIngredientsSection = computed(
  () =>
    editMode.value &&
    !!activeId.value &&
    organisationIngredientsEnabled(organisationsList.value, props.activeOrganisationId),
)

const activeOrganisationCountryId = computed(() => activeOrganisation.value?.country_id ?? null)

const {
  options: taxCodeOptions,
  loading: taxCodesLoading,
} = useTaxCodes(activeOrganisationCountryId)

const {
  options: accountingAccountOptions,
  loading: accountingAccountsLoading,
  categoryDefaultAccountId,
} = useAccountingAccounts(() => props.activeOrganisationId)

const visibleCategories = computed(() =>
  categories.value.filter((category) =>
    matchesActiveOrganisation(props.activeOrganisationId, category.organisation_id)
  )
)

const articlesInActiveOrganisation = computed(() =>
  articles.value.filter((article) =>
    matchesActiveOrganisation(props.activeOrganisationId, article.organisation_id)
  )
)

const categoryOptions = computed(() =>
  visibleCategories.value.map((category) => ({
    value: category.id,
    label: category.name,
  }))
)

const categoryFilterOptions = computed(() => [
  { value: null, label: t('articles.allCategories') },
  ...categoryOptions.value,
])

const canCreateArticles = computed(
  () => props.activeOrganisationId != null && categoryOptions.value.length > 0,
)

const additionOptions = computed(() =>
  articles.value
    .filter(
      (a) =>
        a.is_addition &&
        a.is_active &&
        matchesActiveOrganisation(props.activeOrganisationId, a.organisation_id) &&
        !additionsLocal.value.some((l) => l.addition_article_id === a.id),
    )
    .map((a) => ({
      value: a.id,
      label: `${a.name} (${formatPrice(a.price, a.organisation_currency)})`,
    })),
)

const ingredientOptions = computed(() =>
  ingredientCatalog.value
    .filter(
      (ingredient) =>
        ingredient.is_active &&
        !ingredientsLocal.value.some((l) => l.ingredient_id === ingredient.id),
    )
    .map((ingredient) => ({
      value: ingredient.id,
      label: ingredient.unit ? `${ingredient.name} (${ingredient.unit})` : ingredient.name,
    })),
)

const formRef = ref(null)

const labelRules = computed(() => [
  rules.required,
  (v: string) => String(v || '').length <= 22 || t('articles.labelMaxLength'),
])

const priceRules = computed(() => {
  const base = [rules.requiredNumber]
  if (!form.value.isAddition) base.push(rules.minNumber(0))
  return base
})

const taxCodeRules = computed(() => {
  if (!showTaxCodeField.value) return []
  return [rules.required]
})

function resolveDefaultAccountingAccountId(categoryId: number | null) {
  if (!showAccountingAccountField.value) return null
  const category = categories.value.find((row) => Number(row.id) === Number(categoryId))
  if (category?.accounting_account_id != null) {
    return category.accounting_account_id
  }
  return categoryDefaultAccountId.value
}

watch(
  () => form.value.articleCategoryId,
  (categoryId) => {
    if (editMode.value || categoryId == null) return
    if (form.value.accountingAccountId != null) return
    form.value.accountingAccountId = resolveDefaultAccountingAccountId(categoryId)
  },
)

function defaultTaxCodeIdForActiveOrganisation() {
  if (!showTaxCodeField.value) return null
  return activeOrganisation.value?.default_tax_code_id ?? null
}

function formatPrice(value: number | string, currency = 'EUR') {
  return formatPriceWithCurrency(value, currency || 'EUR', locale.value)
}

function currencyForOrganisationId(organisationId: number | null | undefined) {
  if (organisationId == null) return 'EUR'
  const org = organisationsList.value.find((o) => Number(o.id) === Number(organisationId))
  return org?.currency || 'EUR'
}

function syncFormCurrencyFromContext(article: ArticleRead | null = null) {
  if (article?.organisation_currency) {
    formCurrency.value = article.organisation_currency
    return
  }
  if (article?.organisation_id != null) {
    formCurrency.value = currencyForOrganisationId(article.organisation_id)
    return
  }
  formCurrency.value = currencyForOrganisationId(props.activeOrganisationId)
}

function matchesSearch(article: ArticleRead, term: string) {
  if (!term) return true
  return [
    article.id,
    article.name,
    article.import_article_number,
    article.label,
    article.description,
    article.unit,
    article.accounting_account_number,
    article.price,
    article.article_category_name,
    article.organisation_name,
  ]
    .filter((value) => value !== null && value !== undefined)
    .some((value) => String(value).toLowerCase().includes(term))
}

const filteredArticles = computed(() =>
  filterArticleList(
    articles.value.filter((article) =>
      matchesActiveOrganisation(props.activeOrganisationId, article.organisation_id),
    ),
    {
      search: searchQuery.value,
      categoryId: categoryFilter.value,
      type: typeFilter.value,
      status: statusFilter.value,
    },
    matchesSearch,
  ),
)

const { currentPage, pageSize } = useClientPagination(filteredArticles, {
  resetOn: [searchQuery, categoryFilter, typeFilter, statusFilter, () => props.activeOrganisationId],
})

watch([searchQuery, categoryFilter, typeFilter, statusFilter, () => props.activeOrganisationId], () => {
  if (
    categoryFilter.value != null &&
    !visibleCategories.value.some((category) => Number(category.id) === Number(categoryFilter.value))
  ) {
    categoryFilter.value = null
  }
})

async function fetchArticles() {
  try {
    articles.value = await apiJson<ArticleRead[]>('/articles/')
  } catch {
    message.value = t('articles.loadError')
    messageType.value = 'error'
  }
}

async function fetchCategories() {
  try {
    categories.value = await apiJson<ArticleCategoryRead[]>('/article-categories/')
  } catch {
    message.value = t('articles.categoriesLoadError')
    messageType.value = 'error'
  }
}

function clearFormState() {
  form.value = emptyForm()
  additionsLocal.value = []
  additionPickIds.value = []
  additionsMessage.value = ''
  ingredientsLocal.value = []
  ingredientPickIds.value = []
  ingredientsMessage.value = ''
  if (categoryOptions.value.length > 0) {
    form.value.articleCategoryId = categoryOptions.value[0].value
  }
  form.value.taxCodeId = defaultTaxCodeIdForActiveOrganisation()
  message.value = ''
  syncFormCurrencyFromContext()
}

async function applyArticleToForm(article: ArticleRead) {
  form.value = {
    name: article.name || '',
    label: article.label || '',
    importArticleNumber: article.import_article_number || '',
    description: article.description || '',
    unit: article.unit || '',
    accountingAccountId: article.accounting_account_id ?? null,
    taxCodeId: article.tax_code_id ?? null,
    price: article.price ?? 0,
    isAddition: !!article.is_addition,
    isActive: article.is_active !== false,
    articleCategoryId: article.article_category_id || null,
  }
  message.value = ''
  syncFormCurrencyFromContext(article)
  if (!article.is_addition) {
    await loadAdditions(article.id)
  } else {
    additionsLocal.value = []
  }
  if (organisationIngredientsEnabled(organisationsList.value, props.activeOrganisationId)) {
    await loadArticleIngredients(article.id)
  } else {
    ingredientsLocal.value = []
  }
}

async function syncRouteToForm() {
  if (!showDetail.value) {
    clearFormState()
    return
  }
  if (isCreateMode.value) {
    clearFormState()
    const queryType = route.query.type
    if (queryType === 'addition') {
      typeFilter.value = 'additions'
      form.value.isAddition = true
    } else {
      form.value.isAddition = typeFilter.value === 'additions'
    }
    syncFormCurrencyFromContext()
    return
  }
  const id = routeEntityId.value
  if (id == null) {
    goToList()
    return
  }
  let row = articles.value.find((a) => Number(a.id) === Number(id))
  if (!row) {
    try {
      row = await apiJson<ArticleRead>(`/articles/${id}`)
    } catch {
      message.value = t('articles.notFound')
      messageType.value = 'error'
      goToList()
      return
    }
  }
  await applyArticleToForm(row)
}

watch(() => [route.name, route.params.id], syncRouteToForm, { immediate: true })

function resetForm() {
  goToList()
}

function openCreateForm() {
  goToCreate()
}

async function loadAdditions(articleId: number | string) {
  additionsLocal.value = []
  try {
    const data = await apiJson<ArticleAdditionsRead>(`/articles/${articleId}/additions`)
    additionsLocal.value = (data.items || []).map((row, idx) => ({
      addition_article_id: Number(row.addition_article_id),
      name: String(row.name ?? ''),
      price: Number(row.price ?? 0),
      sort_order: Number(row.sort_order ?? idx),
      preselected: Boolean(row.preselected),
    }))
  } catch {
    additionsLocal.value = []
  }
}

function onArticleRowClick(_event: Event, { item }: { item: ArticleRead }) {
  void editArticle(item)
}

async function editArticle(article: ArticleRead) {
  await applyArticleToForm(article)
  goToDetail(article.id)
}

function onAdditionPick(ids: number | number[]) {
  const list = Array.isArray(ids) ? ids : []
  for (const id of list) {
    const art = articles.value.find((a) => a.id === id)
    if (!art || additionsLocal.value.some((l) => l.addition_article_id === id)) continue
    additionsLocal.value.push({
      addition_article_id: id,
      name: art.name,
      price: art.price,
      sort_order: additionsLocal.value.length,
      preselected: false,
    })
  }
  additionPickIds.value = []
}

function removeAdditionLink(row: AdditionLinkLocal) {
  additionsLocal.value = additionsLocal.value.filter((l) => l.addition_article_id !== row.addition_article_id)
}

async function saveAdditions() {
  if (!activeId.value) return
  additionsMessage.value = ''
  try {
    const data = await apiJson<ArticleAdditionsRead>(`/articles/${activeId.value}/additions`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        items: additionsLocal.value.map((l, idx) => ({
          addition_article_id: l.addition_article_id,
          sort_order: l.sort_order ?? idx,
          preselected: l.preselected,
        })),
      }),
    })
    additionsLocal.value = (data.items || []).map((row, idx) => ({
      addition_article_id: Number(row.addition_article_id),
      name: String(row.name ?? ''),
      price: Number(row.price ?? 0),
      sort_order: Number(row.sort_order ?? idx),
      preselected: Boolean(row.preselected),
    }))
    additionsMessage.value = t('articles.additionsSaved')
    additionsMessageType.value = 'success'
  } catch (e: unknown) {
    additionsMessage.value = isApiError(e) ? e.message || t('common.saveFailed') : t('common.saveFailed')
    additionsMessageType.value = 'error'
  }
}

async function fetchIngredientCatalog() {
  if (props.activeOrganisationId == null) {
    ingredientCatalog.value = []
    return
  }
  try {
    ingredientCatalog.value = await apiJson<IngredientRead[]>(
      `/ingredients/?organisation_id=${props.activeOrganisationId}`,
    )
  } catch {
    ingredientCatalog.value = []
  }
}

async function loadArticleIngredients(articleId: number | string) {
  ingredientsLocal.value = []
  try {
    const data = await apiJson<ArticleIngredientsRead>(`/articles/${articleId}/ingredients`)
    ingredientsLocal.value = (data.items || []).map((row, idx) => ({
      ingredient_id: Number(row.ingredient_id),
      name: String(row.name ?? ''),
      unit: row.unit ?? null,
      amount: Number(row.amount ?? 1),
      sort_order: Number(row.sort_order ?? idx),
    }))
  } catch {
    ingredientsLocal.value = []
  }
}

function onIngredientPick(ids: number | number[]) {
  const list = Array.isArray(ids) ? ids : []
  for (const id of list) {
    const ingredient = ingredientCatalog.value.find((row) => row.id === id)
    if (!ingredient || ingredientsLocal.value.some((l) => l.ingredient_id === id)) continue
    ingredientsLocal.value.push({
      ingredient_id: id,
      name: ingredient.name,
      unit: ingredient.unit,
      amount: 1,
      sort_order: ingredientsLocal.value.length,
    })
  }
  ingredientPickIds.value = []
}

function removeIngredientLink(row: IngredientLinkLocal) {
  ingredientsLocal.value = ingredientsLocal.value.filter((l) => l.ingredient_id !== row.ingredient_id)
}

async function saveIngredients() {
  if (!activeId.value) return
  ingredientsMessage.value = ''
  try {
    const data = await apiJson<ArticleIngredientsRead>(`/articles/${activeId.value}/ingredients`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        items: ingredientsLocal.value.map((l, idx) => ({
          ingredient_id: l.ingredient_id,
          amount: l.amount > 0 ? l.amount : 1,
          sort_order: l.sort_order ?? idx,
        })),
      }),
    })
    ingredientsLocal.value = (data.items || []).map((row, idx) => ({
      ingredient_id: Number(row.ingredient_id),
      name: String(row.name ?? ''),
      unit: row.unit ?? null,
      amount: Number(row.amount ?? 1),
      sort_order: Number(row.sort_order ?? idx),
    }))
    ingredientsMessage.value = t('articles.ingredientsSaved')
    ingredientsMessageType.value = 'success'
  } catch (e: unknown) {
    ingredientsMessage.value = isApiError(e) ? e.message || t('common.saveFailed') : t('common.saveFailed')
    ingredientsMessageType.value = 'error'
  }
}

async function saveArticle() {
  if (props.activeOrganisationId == null) {
    message.value = t('common.noOrganisation')
    messageType.value = 'error'
    return
  }
  if (!(await validateForm(formRef))) return
  const payload = {
    name: form.value.name,
    label: form.value.label,
    price: Number(form.value.price ?? 0),
    import_article_number: form.value.importArticleNumber || null,
    description: form.value.description || null,
    unit: form.value.unit || null,
    accounting_account_id: showAccountingAccountField.value ? form.value.accountingAccountId : null,
    tax_code_id: showTaxCodeField.value ? form.value.taxCodeId : null,
    is_addition: form.value.isAddition,
    is_active: form.value.isActive,
    article_category_id: form.value.articleCategoryId,
  }

  try {
    const path = editMode.value ? `/articles/${activeId.value}` : '/articles/'
    const method = editMode.value ? 'PUT' : 'POST'
    await apiJson(path, {
      method,
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })
    const wasEdit = editMode.value
    await fetchArticles()
    invalidateOrgCatalog(props.activeOrganisationId)
    message.value = wasEdit ? t('articles.updated') : t('articles.created')
    messageType.value = 'success'
    await goToList()
  } catch {
    message.value = t('articles.saveError')
    messageType.value = 'error'
  }
}

async function deleteArticle(id: number | string) {
  if (!confirm(t('articles.deleteConfirm'))) return
  try {
    await apiJson(`/articles/${id}`, {
      method: 'DELETE',
    })
    await fetchArticles()
    invalidateOrgCatalog(props.activeOrganisationId)
    message.value = t('articles.deleted')
    messageType.value = 'success'
    if (Number(routeEntityId.value) === Number(id)) {
      await goToList()
    }
  } catch (error: unknown) {
    message.value = getErrorMessage(error, t('articles.deleteError'))
    messageType.value = 'error'
  }
}

onMounted(async () => {
  await fetchCategories()
  await fetchArticles()
  await fetchIngredientCatalog()
})

watch(
  () => props.activeOrganisationId,
  () => {
    fetchIngredientCatalog()
  },
)
</script>

<style scoped>
.empty-hint {
  color: rgba(var(--v-theme-on-surface), 0.65);
  margin: 0 0 1rem;
}

h2 {
  margin: 0 0 1.5rem;
  color: rgb(var(--v-theme-on-surface));
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  margin-bottom: 1rem;
}

.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.block-hint {
  display: block;
  margin: -0.5rem 0 1rem;
}
.additions-section {
  margin: 1.5rem 0;
  padding-top: 1rem;
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
.additions-section h3 {
  margin: 0 0 0.5rem;
}
.ingredients-section {
  margin: 1.5rem 0;
  padding-top: 1rem;
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
.ingredients-section h3 {
  margin: 0 0 0.5rem;
}
.stock-field {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin: 0.5rem 0 1rem;
}

label {
  color: rgb(var(--v-theme-on-surface));
  font-size: 0.875rem;
  font-weight: 600;
}

small,
.table-header span {
  color: rgba(var(--v-theme-on-surface), 0.65);
  font-size: 0.9rem;
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

.list-controls {
  display: grid;
  grid-template-columns: minmax(240px, 1fr) repeat(3, 200px);
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

.success,
.error {
  margin-top: 1rem;
}

@media (max-width: 1000px) {
  .field-row,
  .list-controls {
    grid-template-columns: 1fr;
  }
}
</style>
