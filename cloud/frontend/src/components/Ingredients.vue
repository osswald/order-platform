<template>
  <ListDetailLayout
    :title="$t('ingredients.title')"
    :subtitle="$t('ingredients.subtitle')"
    :createLabel="$t('ingredients.createLabel')"
    :showCreate="canCreateIngredients"
    :showDetail="showDetail"
    @open-create="openCreateForm"
  >
    <template #detail>
      <h2>{{ editMode ? $t('ingredients.editTitle') : $t('ingredients.newTitle') }}</h2>
      <p class="form-required-legend"><span class="vq-asterisk">*</span> {{ $t('common.requiredLegend') }}</p>

      <v-form ref="formRef" @submit.prevent="saveIngredient">
        <div class="form-field">
          <FormLabel required>{{ $t('common.name') }}</FormLabel>
          <v-text-field
            v-model="form.name"
            :placeholder="$t('ingredients.namePlaceholder')"
            hide-details="auto"
            required
            :rules="[rules.required]"
          />
        </div>

        <div class="form-field">
          <FormLabel>{{ $t('common.unit') }}</FormLabel>
          <v-text-field
            v-model="form.unit"
            :placeholder="$t('ingredients.unitPlaceholder')"
            hide-details="auto"
            maxlength="32"
          />
        </div>

        <div class="form-field toggle-row">
          <FormLabel>{{ $t('ingredients.isActive') }}</FormLabel>
          <v-switch v-model="form.isActive" hide-details density="compact" />
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
        <h2>{{ $t('ingredients.allTitle') }}</h2>
        <span>{{ $t('common.entriesCount', { filtered: filteredIngredients.length, total: ingredientsInActiveOrganisation.length }) }}</span>
      </div>
      <div class="list-controls">
        <div class="search-field">
          <label>{{ $t('common.search') }}</label>
          <v-text-field
            v-model="searchQuery"
            :placeholder="$t('ingredients.searchPlaceholder')"
            prepend-inner-icon="mdi-magnify"
            hide-details="auto"
          />
        </div>
      </div>

      <VqDataTable
        v-model:page="currentPage"
        :headers="tableHeaders"
        :items="filteredIngredients"
        :items-per-page="pageSize"
        item-value="id"
        hover
        :no-data-text="$t('ingredients.noData')"
        class="vq-data-table list-table"
        @click:row="onIngredientRowClick"
      >
        <template #item.is_active="{ item }">
          {{ item.is_active ? $t('common.yes') : $t('common.no') }}
        </template>
        <template #item.unit="{ item }">
          {{ item.unit || $t('common.emDash') }}
        </template>
        <template #item.actions="{ item }">
          <v-btn
            color="error"
            variant="text"
            :disabled="item.usage_count > 0"
            @click.stop="deleteIngredient(item.id)"
          >
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
import { apiJson } from '../api'
import { rules, validateForm } from '../utils/formRules.js'
import { useListDetailRouting } from '../composables/useListDetailRouting'
import { useClientPagination } from '../composables/useClientPagination'
import { matchesActiveOrganisation } from '../utils/orgScope'
import VqDataTable from './VqDataTable.vue'
import type { IngredientRead } from '@/types/api'
import type { IngredientForm } from '@/types/ui'
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
} = useListDetailRouting('ingredients')

const tableHeaders = computed((): DataTableHeader[] => [
  { title: t('common.id'), key: 'id' },
  { title: t('common.name'), key: 'name' },
  { title: t('common.unit'), key: 'unit' },
  { title: t('ingredients.isActive'), key: 'is_active', sortable: false },
  { title: t('common.organisation'), key: 'organisation_name' },
  { title: t('ingredients.usageCount'), key: 'usage_count' },
  { title: t('common.actions'), key: 'actions', sortable: false, align: 'end' },
])

const ingredients = ref<IngredientRead[]>([])
const message = ref('')
const messageType = ref('')
const searchQuery = ref('')

const emptyForm = (): IngredientForm => ({
  name: '',
  unit: '',
  isActive: true,
})

const form = ref<IngredientForm>(emptyForm())
const formRef = ref(null)

const canCreateIngredients = computed(() => props.activeOrganisationId != null)

function matchesSearch(ingredient: IngredientRead, term: string) {
  if (!term) return true
  return [ingredient.id, ingredient.name, ingredient.unit, ingredient.organisation_name]
    .filter((value) => value !== null && value !== undefined)
    .some((value) => String(value).toLowerCase().includes(term))
}

const filteredIngredients = computed(() => {
  const term = searchQuery.value.trim().toLowerCase()
  return ingredients.value.filter((ingredient) => {
    if (!matchesSearch(ingredient, term)) return false
    if (!matchesActiveOrganisation(props.activeOrganisationId, ingredient.organisation_id)) return false
    return true
  })
})

const { currentPage, pageSize } = useClientPagination(filteredIngredients, {
  resetOn: [searchQuery, () => props.activeOrganisationId],
})

const ingredientsInActiveOrganisation = computed(() =>
  ingredients.value.filter((ingredient) =>
    matchesActiveOrganisation(props.activeOrganisationId, ingredient.organisation_id),
  ),
)

onMounted(async () => {
  await fetchIngredients()
})

async function fetchIngredients() {
  try {
    const path =
      props.activeOrganisationId != null
        ? `/ingredients/?organisation_id=${props.activeOrganisationId}`
        : '/ingredients/'
    ingredients.value = await apiJson<IngredientRead[]>(path)
  } catch {
    message.value = t('ingredients.loadError')
    messageType.value = 'error'
  }
}

watch(
  () => props.activeOrganisationId,
  () => {
    fetchIngredients()
  },
)

function applyIngredientToForm(ingredient: IngredientRead) {
  form.value = {
    name: ingredient.name || '',
    unit: ingredient.unit || '',
    isActive: ingredient.is_active !== false,
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
  let row = ingredients.value.find((i) => Number(i.id) === Number(id))
  if (!row) {
    try {
      row = await apiJson<IngredientRead>(`/ingredients/${id}`)
    } catch {
      message.value = t('ingredients.notFound')
      messageType.value = 'error'
      goToList()
      return
    }
  }
  applyIngredientToForm(row)
}

watch(() => [route.name, route.params.id], syncRouteToForm, { immediate: true })

function resetForm() {
  goToList()
}

function openCreateForm() {
  goToCreate()
}

function onIngredientRowClick(_event: Event, { item }: { item: IngredientRead }) {
  editIngredient(item)
}

function editIngredient(ingredient: IngredientRead) {
  applyIngredientToForm(ingredient)
  goToDetail(ingredient.id)
}

async function saveIngredient() {
  if (props.activeOrganisationId == null) {
    message.value = t('common.noOrganisation')
    messageType.value = 'error'
    return
  }
  if (!(await validateForm(formRef))) return
  const payload: {
    name: string
    unit: string | null
    is_active: boolean
    organisation_id?: number
  } = {
    name: form.value.name,
    unit: form.value.unit.trim() || null,
    is_active: form.value.isActive,
  }
  if (!editMode.value && props.activeOrganisationId != null) {
    payload.organisation_id = props.activeOrganisationId
  }

  try {
    const path = editMode.value ? `/ingredients/${routeEntityId.value}` : '/ingredients/'
    const method = editMode.value ? 'PUT' : 'POST'
    await apiJson(path, {
      method,
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })
    const wasEdit = editMode.value
    await fetchIngredients()
    message.value = wasEdit ? t('ingredients.updated') : t('ingredients.created')
    messageType.value = 'success'
    await goToList()
  } catch {
    message.value = t('ingredients.saveError')
    messageType.value = 'error'
  }
}

async function deleteIngredient(id: number | string) {
  if (!confirm(t('ingredients.deleteConfirm'))) return
  try {
    await apiJson(`/ingredients/${id}`, {
      method: 'DELETE',
    })
    await fetchIngredients()
    message.value = t('ingredients.deleted')
    messageType.value = 'success'
    if (Number(routeEntityId.value) === Number(id)) {
      await goToList()
    }
  } catch {
    message.value = t('ingredients.deleteError')
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

.toggle-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  max-width: 28rem;
}
</style>
