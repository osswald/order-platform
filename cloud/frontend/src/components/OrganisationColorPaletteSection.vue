<template>
  <div v-if="organisationId" class="org-color-palette-section">
    <p v-if="loading" class="muted small">{{ t('organisations.colorPalette.loading') }}</p>
    <p v-else-if="loadError" class="error-text">{{ loadError }}</p>
    <template v-else>
      <section class="color-palette-block">
        <div class="block-header">
          <div>
            <div class="section-title-row">
              <h3>{{ t('organisations.colorPalette.sectionTitle') }}</h3>
              <HelpLink slug="organisation-setup" variant="icon" />
            </div>
            <p class="muted small">{{ t('organisations.colorPalette.sectionHint') }}</p>
          </div>
          <v-btn color="primary" size="small" type="button" @click="openCreate">
            {{ t('organisations.colorPalette.addColor') }}
          </v-btn>
        </div>

        <VqDataTable
          :headers="colorHeaders"
          :items="colors"
          item-value="key"
          class="vq-data-table list-table nested-table"
          hide-default-footer
          :no-data-text="t('organisations.colorPalette.noColors')"
        >
          <template #item.color="{ item }">
            <span class="color-swatch" :style="{ background: item.color }" :title="item.color" />
          </template>
          <template #item.actions="{ item }">
            <v-btn size="small" type="button" @click="openEdit(item)">
              {{ t('common.edit') }}
            </v-btn>
            <v-btn color="error" size="small" type="button" @click="deleteColor(item.key)">
              {{ t('common.delete') }}
            </v-btn>
          </template>
        </VqDataTable>
      </section>

      <div class="actions">
        <v-btn color="primary" type="button" :loading="saving" @click="saveAll">
          {{ t('common.save') }}
        </v-btn>
      </div>
      <p v-if="message" :class="messageType">{{ message }}</p>
    </template>

    <v-dialog v-model="dialogOpen" max-width="28rem">
      <v-card>
        <v-card-title>
          {{ editingKey ? t('organisations.colorPalette.editColor') : t('organisations.colorPalette.addColor') }}
        </v-card-title>
        <v-card-text>
          <v-text-field
            v-model="draftLabel"
            :label="t('organisations.colorPalette.colorLabel')"
            maxlength="64"
            hide-details="auto"
            required
            class="dialog-field"
          />
          <div class="form-field">
            <label>{{ t('organisations.colorPalette.colorValue') }}</label>
            <v-color-picker v-model="draftColor" mode="hex" hide-inputs />
            <v-text-field
              v-model="draftColor"
              density="compact"
              hide-details
              placeholder="#eeeeee"
              class="color-hex-input"
            />
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn type="button" @click="dialogOpen = false">{{ t('common.cancel') }}</v-btn>
          <v-btn color="primary" type="button" @click="applyDraft">
            {{ t('organisations.colorPalette.confirmDraft') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { apiJson } from '../api'
import type { ColorPaletteEntry, ColorPaletteRead } from '@/types/api'
import { getErrorMessage } from '@/types/api'
import type { DataTableHeader } from '@/types/vuetify'
import { newUuid } from '@/utils/newUuid'
import VqDataTable from './VqDataTable.vue'
import HelpLink from './HelpLink.vue'

type PaletteRow = ColorPaletteEntry & { key: string }

const props = defineProps<{
  organisationId?: number | null
}>()

const { t } = useI18n()

const loading = ref(false)
const loadError = ref('')
const saving = ref(false)
const message = ref('')
const messageType = ref('success')
const colors = ref<PaletteRow[]>([])

const dialogOpen = ref(false)
const editingKey = ref<string | null>(null)
const draftLabel = ref('')
const draftColor = ref('#EEEEEE')

const colorHeaders = computed((): DataTableHeader[] => [
  { title: t('organisations.colorPalette.colorValue'), key: 'color', sortable: false, width: '4rem' },
  { title: t('organisations.colorPalette.colorLabel'), key: 'label' },
  { title: t('common.actions'), key: 'actions', sortable: false, align: 'end' },
])

function nextKey(): string {
  return `color-${newUuid()}`
}

function mapRows(entries: ColorPaletteEntry[]): PaletteRow[] {
  return entries.map((entry) => ({ ...entry, key: nextKey() }))
}

async function loadPalette() {
  if (!props.organisationId) return
  loading.value = true
  loadError.value = ''
  message.value = ''
  try {
    const data = await apiJson<ColorPaletteRead>(`/organisations/${props.organisationId}/color-palette`)
    colors.value = mapRows(data.colors ?? [])
  } catch (e: unknown) {
    loadError.value = getErrorMessage(e, t('organisations.colorPalette.loadError'))
  } finally {
    loading.value = false
  }
}

async function saveAll() {
  if (!props.organisationId) return
  saving.value = true
  message.value = ''
  try {
    const payload = {
      colors: colors.value.map(({ label, color }) => ({ label, color })),
    }
    const data = await apiJson<ColorPaletteRead>(`/organisations/${props.organisationId}/color-palette`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    colors.value = mapRows(data.colors ?? [])
    message.value = t('organisations.colorPalette.saved')
    messageType.value = 'success'
  } catch (e: unknown) {
    message.value = getErrorMessage(e, t('organisations.colorPalette.saveError'))
    messageType.value = 'error'
  } finally {
    saving.value = false
  }
}

function openCreate() {
  editingKey.value = null
  draftLabel.value = ''
  draftColor.value = '#EEEEEE'
  dialogOpen.value = true
}

function openEdit(item: PaletteRow) {
  editingKey.value = item.key
  draftLabel.value = item.label
  draftColor.value = item.color
  dialogOpen.value = true
}

function applyDraft() {
  const label = draftLabel.value.trim()
  if (!label) return
  const color = draftColor.value.trim() || '#EEEEEE'
  if (editingKey.value) {
    colors.value = colors.value.map((entry) =>
      entry.key === editingKey.value ? { ...entry, label, color } : entry,
    )
  } else {
    colors.value = [...colors.value, { key: nextKey(), label, color }]
  }
  dialogOpen.value = false
}

function deleteColor(key: string) {
  if (!confirm(t('organisations.colorPalette.deleteConfirm'))) return
  colors.value = colors.value.filter((entry) => entry.key !== key)
}

watch(
  () => props.organisationId,
  () => {
    void loadPalette()
  },
  { immediate: true },
)
</script>

<style scoped>
.org-color-palette-section {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.color-palette-block {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.block-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.block-header h3 {
  margin: 0;
}

.section-title-row {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.actions {
  display: flex;
  gap: 0.75rem;
}

.color-swatch {
  display: inline-block;
  width: 2rem;
  height: 2rem;
  border-radius: 6px;
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-top: 1rem;
}

.dialog-field {
  margin-bottom: 0.5rem;
}

.color-hex-input {
  max-width: 10rem;
}
</style>
