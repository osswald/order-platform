<template>
  <div v-if="organisationId" class="org-ingredients-section">
    <p v-if="loading" class="muted small">{{ t('organisations.ingredients.loading') }}</p>
    <p v-else-if="loadError" class="error-text">{{ loadError }}</p>
    <template v-else>
      <section class="ingredients-block">
        <h3>{{ t('organisations.ingredients.sectionTitle') }}</h3>
        <div class="toggle-block">
          <div class="toggle-row">
            <label for="org-ingredients-enabled">
              {{ t('organisations.ingredients.enabled') }}
            </label>
            <v-switch
              id="org-ingredients-enabled"
              v-model="enabled"
              hide-details
              density="compact"
            />
          </div>
        </div>
        <p class="muted small">{{ t('organisations.ingredients.enabledHint') }}</p>
      </section>

      <div class="actions">
        <v-btn color="primary" type="button" :loading="saving" @click="saveAll">
          {{ t('common.save') }}
        </v-btn>
      </div>
      <p v-if="message" :class="messageType">{{ message }}</p>
    </template>
  </div>
</template>

<script setup lang="ts">
import { inject, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { apiJson } from '../api'
import type { OrganisationRead } from '@/types/api'
import { getErrorMessage } from '@/types/api'
import { SESSION_CONTEXT_KEY } from '../sessionContext'
import type { SessionContext } from '@/types/ui'

const props = defineProps<{
  organisationId?: number | null
}>()

const { t } = useI18n()
const sessionContext = inject<SessionContext | null>(SESSION_CONTEXT_KEY, null)

const loading = ref(false)
const loadError = ref('')
const saving = ref(false)
const message = ref('')
const messageType = ref('success')
const enabled = ref(false)

async function loadSettings() {
  if (!props.organisationId) return
  loading.value = true
  loadError.value = ''
  message.value = ''
  try {
    const org = await apiJson<OrganisationRead>(`/organisations/${props.organisationId}`)
    enabled.value = Boolean(org.ingredients_enabled)
  } catch (e: unknown) {
    loadError.value = getErrorMessage(e, t('organisations.ingredients.loadError'))
  } finally {
    loading.value = false
  }
}

async function saveAll() {
  if (!props.organisationId) return
  saving.value = true
  message.value = ''
  try {
    const data = await apiJson<OrganisationRead>(`/organisations/${props.organisationId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ingredients_enabled: enabled.value }),
    })
    enabled.value = Boolean(data.ingredients_enabled)
    message.value = t('organisations.ingredients.saved')
    messageType.value = 'success'
    await sessionContext?.reloadOrganisationsAndSelect?.(Number(props.organisationId))
  } catch (e: unknown) {
    message.value = getErrorMessage(e, t('organisations.ingredients.saveError'))
    messageType.value = 'error'
  } finally {
    saving.value = false
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
.org-ingredients-section {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.ingredients-block {
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

.actions {
  display: flex;
  gap: 0.75rem;
}
</style>
