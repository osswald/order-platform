<template>
  <div v-if="organisationId" class="org-position-comments-section">
    <p v-if="loading" class="muted small">{{ t('organisations.positionComments.loading') }}</p>
    <p v-else-if="loadError" class="error-text">{{ loadError }}</p>
    <template v-else>
      <section class="position-comments-block">
        <h3>{{ t('organisations.positionComments.sectionTitle') }}</h3>
        <div class="toggle-block">
          <div class="toggle-row">
            <label for="org-position-comments-enabled">
              {{ t('organisations.positionComments.enabled') }}
            </label>
            <v-switch
              id="org-position-comments-enabled"
              v-model="enabled"
              hide-details
              density="compact"
            />
          </div>
        </div>
        <p class="muted small">{{ t('organisations.positionComments.enabledHint') }}</p>
      </section>

      <template v-if="enabled">
        <section class="position-comments-block">
          <div class="block-header">
            <h3>{{ t('organisations.positionComments.presetsTitle') }}</h3>
            <v-btn color="primary" size="small" type="button" @click="openCreate">
              {{ t('organisations.positionComments.addPreset') }}
            </v-btn>
          </div>
          <p class="muted small">{{ t('organisations.positionComments.presetsHint') }}</p>

          <VqDataTable
            :headers="presetHeaders"
            :items="presets"
            item-value="id"
            class="vq-data-table list-table nested-table"
            hide-default-footer
            :no-data-text="t('organisations.positionComments.noPresets')"
          >
            <template #item.actions="{ item }">
              <v-btn variant="text" size="small" type="button" @click="openEdit(item)">
                {{ t('common.edit') }}
              </v-btn>
              <v-btn color="error" variant="text" size="small" type="button" @click="deletePreset(item.id)">
                {{ t('common.delete') }}
              </v-btn>
            </template>
          </VqDataTable>
        </section>
      </template>

      <div class="actions">
        <v-btn color="primary" type="button" :loading="saving" @click="saveAll">
          {{ t('common.save') }}
        </v-btn>
      </div>
      <p v-if="message" :class="messageType">{{ message }}</p>
    </template>

    <v-dialog v-model="dialogOpen" max-width="480">
      <v-card>
        <v-card-title>
          {{ editingId ? t('organisations.positionComments.editPreset') : t('organisations.positionComments.addPreset') }}
        </v-card-title>
        <v-card-text>
          <v-text-field
            v-model="draftText"
            :label="t('organisations.positionComments.presetText')"
            maxlength="512"
            hide-details="auto"
            required
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" type="button" @click="dialogOpen = false">{{ t('common.cancel') }}</v-btn>
          <v-btn color="primary" type="button" :loading="presetSaving" @click="savePreset">
            {{ t('common.save') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { apiJson } from '../api'
import VqDataTable from './VqDataTable.vue'

const props = defineProps({
  organisationId: { type: Number, default: null },
})

const { t } = useI18n()

const loading = ref(false)
const loadError = ref('')
const saving = ref(false)
const message = ref('')
const messageType = ref('success')
const enabled = ref(false)
const presets = ref([])

const dialogOpen = ref(false)
const editingId = ref(null)
const draftText = ref('')
const presetSaving = ref(false)

const presetHeaders = computed(() => [
  { title: t('organisations.positionComments.presetText'), key: 'text' },
  { title: t('common.actions'), key: 'actions', sortable: false, align: 'end' },
])

async function loadSettings() {
  if (!props.organisationId) return
  loading.value = true
  loadError.value = ''
  message.value = ''
  try {
    const [org, presetsData] = await Promise.all([
      apiJson(`/organisations/${props.organisationId}`),
      apiJson(`/organisations/${props.organisationId}/position-comments`),
    ])
    enabled.value = Boolean(org.position_comments_enabled)
    presets.value = presetsData
  } catch (e) {
    loadError.value = e.message || t('organisations.positionComments.loadError')
  } finally {
    loading.value = false
  }
}

async function saveAll() {
  if (!props.organisationId) return
  saving.value = true
  message.value = ''
  try {
    const data = await apiJson(`/organisations/${props.organisationId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ position_comments_enabled: enabled.value }),
    })
    enabled.value = Boolean(data.position_comments_enabled)
    if (!enabled.value) {
      presets.value = []
    } else {
      await loadPresets()
    }
    message.value = t('organisations.positionComments.saved')
    messageType.value = 'success'
  } catch (e) {
    message.value = e.message || t('organisations.positionComments.saveError')
    messageType.value = 'error'
  } finally {
    saving.value = false
  }
}

async function loadPresets() {
  if (!props.organisationId) return
  presets.value = await apiJson(`/organisations/${props.organisationId}/position-comments`)
}

function openCreate() {
  editingId.value = null
  draftText.value = ''
  dialogOpen.value = true
}

function openEdit(item) {
  editingId.value = item.id
  draftText.value = item.text
  dialogOpen.value = true
}

async function savePreset() {
  const text = draftText.value.trim()
  if (!text || !props.organisationId) return
  presetSaving.value = true
  try {
    const path = editingId.value
      ? `/organisations/${props.organisationId}/position-comments/${editingId.value}`
      : `/organisations/${props.organisationId}/position-comments`
    await apiJson(path, {
      method: editingId.value ? 'PUT' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    })
    dialogOpen.value = false
    await loadPresets()
    message.value = t('organisations.positionComments.presetSaved')
    messageType.value = 'success'
  } catch (e) {
    message.value = e.message || t('organisations.positionComments.presetSaveError')
    messageType.value = 'error'
  } finally {
    presetSaving.value = false
  }
}

async function deletePreset(id) {
  if (!props.organisationId) return
  if (!confirm(t('organisations.positionComments.deleteConfirm'))) return
  try {
    await apiJson(`/organisations/${props.organisationId}/position-comments/${id}`, {
      method: 'DELETE',
    })
    await loadPresets()
    message.value = t('organisations.positionComments.presetDeleted')
    messageType.value = 'success'
  } catch (e) {
    message.value = e.message || t('organisations.positionComments.deleteError')
    messageType.value = 'error'
  }
}

watch(
  () => props.organisationId,
  () => {
    loadSettings()
  },
  { immediate: true },
)
</script>

<style scoped>
.org-position-comments-section {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.position-comments-block {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.toggle-block {
  margin-top: 0.25rem;
}

.toggle-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  max-width: 28rem;
}

.block-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.actions {
  display: flex;
  gap: 0.75rem;
}
</style>
