<template>
  <div v-if="organisationId" class="org-vat-section">
    <p v-if="loading" class="muted small">{{ t('organisations.vat.loading') }}</p>
    <p v-else-if="loadError" class="error-text">{{ loadError }}</p>
    <template v-else>
      <div class="toggle-block">
        <div class="toggle-row">
          <label for="org-vat-liable">{{ t('organisations.vat.vatLiable') }}</label>
          <v-switch
            id="org-vat-liable"
            v-model="vatLiable"
            hide-details
            density="compact"
          />
        </div>
      </div>

      <div v-if="vatLiable" class="form-field">
        <v-select
          v-model="defaultTaxCodeId"
          :items="taxCodeOptions"
          item-title="title"
          item-value="value"
          :label="t('organisations.vat.defaultTaxCode')"
          :loading="taxCodesLoading"
          hide-details="auto"
          required
        />
        <p v-if="taxCodesLoadError" class="error-text small">{{ taxCodesLoadError }}</p>
      </div>

      <div class="actions">
        <v-btn
          color="primary"
          type="button"
          :disabled="saving || !countryId"
          :loading="saving"
          @click="save"
        >
          {{ t('common.save') }}
        </v-btn>
      </div>
      <p v-if="message" :class="messageType">{{ message }}</p>
    </template>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { apiFetch } from '../api'
import { useTaxCodes } from '../composables/useTaxCodes'

const { t } = useI18n()

const props = defineProps({
  organisationId: { type: [Number, String], default: null },
  countryId: { type: [Number, String], default: null },
})

const loading = ref(false)
const loadError = ref('')
const saving = ref(false)
const message = ref('')
const messageType = ref('')
const vatLiable = ref(false)
const defaultTaxCodeId = ref(null)

const {
  options: taxCodeOptions,
  loading: taxCodesLoading,
  loadError: taxCodesLoadError,
} = useTaxCodes(() => props.countryId)

async function loadOrganisation() {
  if (!props.organisationId) return
  loading.value = true
  loadError.value = ''
  message.value = ''
  try {
    const res = await apiFetch(`/organisations/${props.organisationId}`)
    if (!res.ok) throw new Error(await res.text())
    const data = await res.json()
    vatLiable.value = Boolean(data.vat_liable)
    defaultTaxCodeId.value = data.default_tax_code_id ?? null
  } catch (e) {
    loadError.value = e.message || t('organisations.vat.loadError')
  } finally {
    loading.value = false
  }
}

async function save() {
  if (!props.organisationId) return
  saving.value = true
  message.value = ''
  try {
    const payload = {
      vat_liable: vatLiable.value,
      default_tax_code_id: vatLiable.value ? defaultTaxCodeId.value : null,
    }
    const res = await apiFetch(`/organisations/${props.organisationId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || t('organisations.vat.saveError'))
    }
    const data = await res.json()
    vatLiable.value = Boolean(data.vat_liable)
    defaultTaxCodeId.value = data.default_tax_code_id ?? null
    message.value = t('organisations.vat.saved')
    messageType.value = 'success'
  } catch (e) {
    message.value = e.message || t('organisations.vat.saveError')
    messageType.value = 'error'
  } finally {
    saving.value = false
  }
}

watch(
  () => [props.organisationId, props.countryId],
  () => {
    loadOrganisation()
  },
  { immediate: true },
)

watch(vatLiable, (enabled) => {
  if (!enabled) {
    defaultTaxCodeId.value = null
  }
})
</script>

<style scoped>
.org-vat-section {
  max-width: 32rem;
}

.toggle-block {
  margin-bottom: 1rem;
}

.toggle-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.toggle-row label {
  font-weight: 500;
}

.form-field {
  margin-bottom: 1rem;
}

.actions {
  margin-top: 1rem;
}

.error-text {
  color: rgb(var(--v-theme-error));
}

.error-text.small {
  margin-top: 0.35rem;
  font-size: 0.875rem;
}

.success {
  color: rgb(var(--v-theme-success));
}
</style>
