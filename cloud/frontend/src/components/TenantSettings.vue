<template>
  <div class="tenant-settings">
    <div class="tenant-settings-header">
      <div>
        <h1>{{ $t('tenantSettings.title') }}</h1>
        <p class="muted">{{ $t('tenantSettings.subtitle') }}</p>
      </div>
      <HelpLink slug="tenant-settings" variant="icon" />
    </div>
    <p class="form-required-legend"><span class="vq-asterisk">*</span> {{ $t('common.requiredLegend') }}</p>

    <v-form v-if="hireCompanyId" ref="formRef" @submit.prevent="saveCompany">
      <div class="form-field">
        <FormLabel required>{{ $t('common.name') }}</FormLabel>
        <v-text-field
          v-model="form.name"
          :placeholder="$t('hireCompanies.namePlaceholder')"
          hide-details="auto"
          required
          :rules="[rules.required]"
        />
      </div>
      <div class="form-field">
        <label>{{ $t('common.address') }}</label>
        <v-text-field v-model="form.address" :placeholder="$t('hireCompanies.addressPlaceholder')" hide-details="auto" />
      </div>
      <div class="field-row">
        <div class="form-field">
          <label>{{ $t('common.zip') }}</label>
          <v-text-field v-model="form.zip" :placeholder="$t('hireCompanies.zipPlaceholder')" hide-details="auto" />
        </div>
        <div class="form-field">
          <label>{{ $t('common.city') }}</label>
          <v-text-field v-model="form.city" :placeholder="$t('hireCompanies.cityPlaceholder')" hide-details="auto" />
        </div>
      </div>
      <div class="form-field">
        <label>{{ $t('common.country') }}</label>
        <v-select
          v-model="form.countryId"
          :items="countryOptions"
          item-title="title"
          item-value="value"
          :placeholder="$t('hireCompanies.countryPlaceholder')"
          hide-details="auto"
          clearable
        />
      </div>
      <ReceiptPrintingSection
        :api-base-path="`/hire-companies/${hireCompanyId}`"
        :entity-id="hireCompanyId"
        :title="$t('hireCompanies.receiptTemplatesTitle')"
        :hint="$t('hireCompanies.receiptTemplatesHint')"
      />
      <div class="actions">
        <v-btn color="primary" type="submit">{{ $t('common.save') }}</v-btn>
      </div>
      <p v-if="message" :class="messageType">{{ message }}</p>
    </v-form>
    <p v-else class="muted">{{ $t('tenantSettings.noHireCompany') }}</p>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import FormLabel from './FormLabel.vue'
import HelpLink from './HelpLink.vue'
import ReceiptPrintingSection from './ReceiptPrintingSection.vue'
import { apiFetch } from '../api'
import { useCountries } from '../composables/useCountries'
import { rules, validateForm } from '../utils/formRules.js'

const props = defineProps({
  activeHireCompanyId: { type: Number, default: null },
})

const { t } = useI18n()
const { countryOptions, fetchCountries } = useCountries()

const hireCompanyId = computed(() => props.activeHireCompanyId)
const form = ref({
  name: '',
  address: '',
  zip: '',
  city: '',
  countryId: null,
})
const formRef = ref(null)
const message = ref('')
const messageType = ref('')

let loadSeq = 0

function resetForm() {
  form.value = {
    name: '',
    address: '',
    zip: '',
    city: '',
    countryId: null,
  }
}

async function loadCompany() {
  const id = hireCompanyId.value
  message.value = ''
  messageType.value = ''
  if (!id) {
    resetForm()
    return
  }
  const seq = ++loadSeq
  try {
    const resp = await apiFetch(`/hire-companies/${id}`)
    if (!resp.ok) throw new Error(await resp.text())
    const data = await resp.json()
    if (seq !== loadSeq || id !== hireCompanyId.value) return
    form.value = {
      name: data.name || '',
      address: data.address || '',
      zip: data.zip || '',
      city: data.city || '',
      countryId: data.country_id ?? data.country?.id ?? null,
    }
  } catch {
    if (seq !== loadSeq || id !== hireCompanyId.value) return
    message.value = t('tenantSettings.loadError')
    messageType.value = 'error'
  }
}

watch(hireCompanyId, () => {
  loadCompany()
}, { immediate: true })

fetchCountries()

async function saveCompany() {
  if (!(await validateForm(formRef))) return
  if (!hireCompanyId.value) return
  try {
    const resp = await apiFetch(`/hire-companies/${hireCompanyId.value}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: form.value.name,
        address: form.value.address || null,
        zip: form.value.zip || null,
        city: form.value.city || null,
        country_id: form.value.countryId || null,
      }),
    })
    if (!resp.ok) throw new Error(await resp.text())
    message.value = t('tenantSettings.saved')
    messageType.value = 'success'
  } catch {
    message.value = t('tenantSettings.saveError')
    messageType.value = 'error'
  }
}

</script>

<style scoped>
.tenant-settings {
  max-width: 720px;
}

.tenant-settings-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.5rem;
}

.tenant-settings-header h1 {
  margin: 0 0 0.35rem;
}

.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.actions {
  margin-top: 1.5rem;
}

.muted {
  color: rgba(var(--v-theme-on-surface), 0.6);
}
</style>
