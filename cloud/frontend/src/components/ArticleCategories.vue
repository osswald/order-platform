<template>
  <ListDetailLayout
    :title="$t('articleCategories.title')"
    :subtitle="$t('articleCategories.subtitle')"
    :createLabel="$t('articleCategories.createLabel')"
    :showCreate="canCreateCategories"
    :showDetail="showDetail"
    @open-create="openCreateForm"
  >
    <template #detail>
      <h2>{{ editMode ? $t('articleCategories.editTitle') : $t('articleCategories.newTitle') }}</h2>
      <p class="form-required-legend"><span class="vq-asterisk">*</span> {{ $t('common.requiredLegend') }}</p>

      <v-form ref="formRef" @submit.prevent="saveCategory">
        <div class="form-field">
          <FormLabel required>{{ $t('common.name') }}</FormLabel>
          <v-text-field
            v-model="form.name"
            :placeholder="$t('articleCategories.namePlaceholder')"
            hide-details="auto"
            required
            :rules="[rules.required]"
          />
        </div>

        <div v-if="showAccountingAccountField" class="form-field">
          <v-select
            v-model="form.accountingAccountId"
            :items="accountingAccountOptions"
            item-title="title"
            item-value="value"
            :label="$t('articleCategories.accountingAccount')"
            :placeholder="$t('common.optional')"
            :loading="accountingAccountsLoading"
            hide-details="auto"
            clearable
          />
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
        <h2>{{ $t('articleCategories.allTitle') }}</h2>
        <span>{{ $t('common.entriesCount', { filtered: filteredCategories.length, total: categoriesInActiveOrganisation.length }) }}</span>
      </div>
      <div class="list-controls">
        <div class="search-field">
          <label>{{ $t('common.search') }}</label>
          <v-text-field
            v-model="searchQuery"
            :placeholder="$t('articleCategories.searchPlaceholder')"
            prepend-inner-icon="mdi-magnify"
            hide-details="auto"
          />
        </div>
      </div>

      <VqDataTable
        v-model:page="currentPage"
        :headers="tableHeaders"
        :items="filteredCategories"
        :items-per-page="pageSize"
        item-value="id"
        hover
        :no-data-text="$t('articleCategories.noData')"
        class="vq-data-table list-table"
        @click:row="onCategoryRowClick"
      >
        <template #item.actions="{ item }">
          <v-btn
            color="error"
            variant="text"
            :disabled="item.article_count > 0"
            @click.stop="deleteCategory(item.id)"
          >
            {{ $t('common.delete') }}
          </v-btn>
        </template>
      </VqDataTable>
    </template>
  </ListDetailLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, inject } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import FormLabel from './FormLabel.vue'
import ListDetailLayout from './ListDetailLayout.vue'
import { apiJson } from '../api'
import { rules, validateForm } from '../utils/formRules.js'
import { useListDetailRouting } from '../composables/useListDetailRouting'
import { useClientPagination } from '../composables/useClientPagination'
import { matchesActiveOrganisation, organisationAccountsEnabled } from '../utils/orgScope'
import { useAccountingAccounts } from '../composables/useAccountingAccounts'
import { SESSION_CONTEXT_KEY } from '../sessionContext'
import VqDataTable from './VqDataTable.vue'
import type { ArticleCategoryRead } from '@/types/api'
import type { AccessibleOrganisation, ArticleCategoryForm, SessionContext } from '@/types/ui'
import type { DataTableHeader } from '@/types/vuetify'

const { t } = useI18n()

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
} = useListDetailRouting('article-categories')

const tableHeaders = computed((): DataTableHeader[] => [
  { title: t('common.id'), key: 'id' },
  { title: t('common.name'), key: 'name' },
  { title: t('common.organisation'), key: 'organisation_name' },
  { title: t('articleCategories.articlesCount'), key: 'article_count' },
  { title: t('common.actions'), key: 'actions', sortable: false, align: 'end' },
])

const categories = ref<ArticleCategoryRead[]>([])
const sessionContext = inject<SessionContext | null>(SESSION_CONTEXT_KEY, null)
const organisationsList = computed(
  () => (sessionContext?.accessibleOrganisations?.value ?? []) as AccessibleOrganisation[],
)
const message = ref('')
const messageType = ref('')
const searchQuery = ref('')

const emptyForm = () => ({
  name: '',
  accountingAccountId: null,
})

const form = ref<ArticleCategoryForm>(emptyForm())
const formRef = ref(null)

const showAccountingAccountField = computed(() =>
  organisationAccountsEnabled(organisationsList.value, props.activeOrganisationId),
)

const {
  options: accountingAccountOptions,
  loading: accountingAccountsLoading,
  categoryDefaultAccountId,
} = useAccountingAccounts(() => props.activeOrganisationId)

const canCreateCategories = computed(() => props.activeOrganisationId != null)

function matchesSearch(category: ArticleCategoryRead, term: string) {
  if (!term) return true
  return [category.id, category.name, category.organisation_name]
    .filter((value) => value !== null && value !== undefined)
    .some((value) => String(value).toLowerCase().includes(term))
}

const filteredCategories = computed(() => {
  const term = searchQuery.value.trim().toLowerCase()
  return categories.value.filter((category) => {
    if (!matchesSearch(category, term)) return false
    if (!matchesActiveOrganisation(props.activeOrganisationId, category.organisation_id)) return false
    return true
  })
})

const { currentPage, pageSize } = useClientPagination(filteredCategories, {
  resetOn: [searchQuery, () => props.activeOrganisationId],
})

const categoriesInActiveOrganisation = computed(() =>
  categories.value.filter((category) =>
    matchesActiveOrganisation(props.activeOrganisationId, category.organisation_id)
  )
)

onMounted(async () => {
  await fetchCategories()
})

async function fetchCategories() {
  try {
    categories.value = await apiJson<ArticleCategoryRead[]>('/article-categories/')
  } catch {
    message.value = t('articleCategories.loadError')
    messageType.value = 'error'
  }
}

function applyCategoryToForm(category: ArticleCategoryRead) {
  form.value = {
    name: category.name || '',
    accountingAccountId: category.accounting_account_id ?? null,
  }
  message.value = ''
}

function clearFormState() {
  form.value = {
    name: '',
    accountingAccountId: categoryDefaultAccountId.value,
  }
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
  let row = categories.value.find((c) => Number(c.id) === Number(id))
  if (!row) {
    try {
      row = await apiJson<ArticleCategoryRead>(`/article-categories/${id}`)
    } catch {
      message.value = t('articleCategories.notFound')
      messageType.value = 'error'
      goToList()
      return
    }
  }
  applyCategoryToForm(row)
}

watch(() => [route.name, route.params.id], syncRouteToForm, { immediate: true })

function resetForm() {
  goToList()
}

function openCreateForm() {
  goToCreate()
}

function onCategoryRowClick(_event: Event, { item }: { item: ArticleCategoryRead }) {
  editCategory(item)
}

function editCategory(category: ArticleCategoryRead) {
  applyCategoryToForm(category)
  goToDetail(category.id)
}

async function saveCategory() {
  if (props.activeOrganisationId == null) {
    message.value = t('common.noOrganisation')
    messageType.value = 'error'
    return
  }
  if (!(await validateForm(formRef))) return
  const payload: {
    name: string
    accounting_account_id: number | null
    organisation_id?: number
  } = {
    name: form.value.name,
    accounting_account_id: showAccountingAccountField.value ? form.value.accountingAccountId : null,
  }
  if (!editMode.value && props.activeOrganisationId != null) {
    payload.organisation_id = props.activeOrganisationId
  }

  try {
    const path = editMode.value
      ? `/article-categories/${routeEntityId.value}`
      : '/article-categories/'
    const method = editMode.value ? 'PUT' : 'POST'
    await apiJson(path, {
      method,
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })
    const wasEdit = editMode.value
    await fetchCategories()
    message.value = wasEdit ? t('articleCategories.updated') : t('articleCategories.created')
    messageType.value = 'success'
    await goToList()
  } catch {
    message.value = t('articleCategories.saveError')
    messageType.value = 'error'
  }
}

async function deleteCategory(id: number | string) {
  if (!confirm(t('articleCategories.deleteConfirm'))) return
  try {
    await apiJson(`/article-categories/${id}`, {
      method: 'DELETE',
    })
    await fetchCategories()
    message.value = t('articleCategories.deleted')
    messageType.value = 'success'
    if (Number(routeEntityId.value) === Number(id)) {
      await goToList()
    }
  } catch {
    message.value = t('articleCategories.deleteError')
    messageType.value = 'error'
  }
}

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
