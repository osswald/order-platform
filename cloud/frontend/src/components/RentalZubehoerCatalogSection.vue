<template>
  <section v-if="hireCompanyId" class="zubehoer-catalog-section">
    <div class="section-header">
      <div>
        <h3>{{ t('tenantSettings.zubehoer.title') }}</h3>
        <p class="muted small">{{ t('tenantSettings.zubehoer.hint') }}</p>
      </div>
      <v-btn color="primary" size="small" type="button" data-testid="zubehoer-add" @click="openCreate">
        {{ t('tenantSettings.zubehoer.add') }}
      </v-btn>
    </div>

    <p v-if="loading" class="muted small">{{ t('common.loading') }}</p>
    <p v-else-if="loadError" class="error-text">{{ loadError }}</p>
    <p v-else-if="!items.length" class="muted small">{{ t('tenantSettings.zubehoer.empty') }}</p>
    <ul v-else class="catalog-list">
      <li v-for="item in items" :key="item.id" class="catalog-row">
        <span>
          {{ item.name }}
          <span v-if="item.default_quantity != null" class="muted">({{ item.default_quantity }})</span>
          <span v-if="!item.is_active" class="muted"> — {{ t('tenantSettings.zubehoer.inactive') }}</span>
        </span>
        <span class="row-actions">
          <v-btn size="small" type="button" @click="openEdit(item)">{{ t('common.edit') }}</v-btn>
          <v-btn color="error" size="small" type="button" @click="removeItem(item.id)">{{ t('common.delete') }}</v-btn>
        </span>
      </li>
    </ul>

    <v-dialog v-model="dialogOpen" max-width="480">
      <v-card>
        <v-card-title>
          {{ editingId ? t('tenantSettings.zubehoer.edit') : t('tenantSettings.zubehoer.add') }}
        </v-card-title>
        <v-card-text>
          <v-text-field v-model="draftName" :label="t('common.name')" hide-details="auto" class="mb-3" />
          <v-text-field
            v-model="draftDefaultQty"
            type="number"
            min="1"
            :label="t('tenantSettings.zubehoer.defaultQtyOptional')"
            hide-details="auto"
            class="mb-3"
          />
          <v-switch v-model="draftActive" :label="t('tenantSettings.zubehoer.active')" hide-details density="compact" />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn type="button" @click="dialogOpen = false">{{ t('common.cancel') }}</v-btn>
          <v-btn color="primary" type="button" :loading="saving" @click="saveItem">{{ t('common.save') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </section>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { apiJson } from '../api'
import type { RentalZubehoerCatalogRead } from '@/types/api'

const props = defineProps<{ hireCompanyId?: number | null }>()

const { t } = useI18n()
const items = ref<RentalZubehoerCatalogRead[]>([])
const loading = ref(false)
const loadError = ref('')
const dialogOpen = ref(false)
const editingId = ref<number | null>(null)
const draftName = ref('')
const draftDefaultQty = ref('')
const draftActive = ref(true)
const saving = ref(false)

async function loadItems() {
  if (!props.hireCompanyId) {
    items.value = []
    return
  }
  loading.value = true
  loadError.value = ''
  try {
    items.value = await apiJson<RentalZubehoerCatalogRead[]>('/rental-zubehoer-catalog/')
  } catch {
    loadError.value = t('tenantSettings.zubehoer.loadError')
    items.value = []
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  draftName.value = ''
  draftDefaultQty.value = ''
  draftActive.value = true
  dialogOpen.value = true
}

function openEdit(item: RentalZubehoerCatalogRead) {
  editingId.value = item.id
  draftName.value = item.name
  draftDefaultQty.value = item.default_quantity != null ? String(item.default_quantity) : ''
  draftActive.value = item.is_active
  dialogOpen.value = true
}

function parseDefaultQty(): number | null {
  const trimmed = draftDefaultQty.value.trim()
  if (!trimmed) return null
  const parsed = Number.parseInt(trimmed, 10)
  return Number.isFinite(parsed) && parsed >= 1 ? parsed : null
}

async function saveItem() {
  const name = draftName.value.trim()
  if (!name) return
  saving.value = true
  try {
    const payload = {
      name,
      default_quantity: parseDefaultQty(),
      is_active: draftActive.value,
    }
    if (editingId.value != null) {
      await apiJson(`/rental-zubehoer-catalog/${editingId.value}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
    } else {
      await apiJson('/rental-zubehoer-catalog/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
    }
    dialogOpen.value = false
    await loadItems()
  } finally {
    saving.value = false
  }
}

async function removeItem(id: number) {
  if (!confirm(t('tenantSettings.zubehoer.deleteConfirm'))) return
  await apiJson(`/rental-zubehoer-catalog/${id}`, { method: 'DELETE' })
  await loadItems()
}

watch(
  () => props.hireCompanyId,
  () => {
    void loadItems()
  },
  { immediate: true },
)
</script>

<style scoped>
.zubehoer-catalog-section {
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid rgba(var(--v-border-color), 0.2);
}

.section-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.75rem;
}

.section-header h3 {
  margin: 0 0 0.25rem;
}

.catalog-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.catalog-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.row-actions {
  display: flex;
  gap: 0.35rem;
  flex-shrink: 0;
}

.muted {
  opacity: 0.7;
}

.small {
  font-size: 0.875rem;
}

.error-text {
  color: rgb(var(--v-theme-error));
}
</style>
