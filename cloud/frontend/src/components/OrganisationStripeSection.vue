<template>
  <div v-if="organisationId" class="org-stripe-block">
    <div class="stripe-header-row">
      <h3>{{ t('stripe.sectionTitle') }}</h3>
      <HelpLink slug="stripe-connect" variant="icon" />
    </div>
    <p class="muted small">
      {{ t('stripe.sectionDescription') }}
    </p>

    <p v-if="loading" class="muted small">{{ t('stripe.loadingStatus') }}</p>
    <p v-else-if="loadError" class="error-text">{{ loadError }}</p>
    <template v-else-if="status">
      <p v-if="!status.configured" class="error-text">{{ status.error }}</p>
      <template v-else>
        <div class="stripe-chips">
          <v-chip size="small" :color="status.charges_enabled ? 'success' : 'default'" variant="tonal">
            {{ t('stripe.charges') }}: {{ status.charges_enabled ? t('stripe.active') : t('stripe.pending') }}
          </v-chip>
          <v-chip size="small" :color="status.payouts_enabled ? 'success' : 'default'" variant="tonal">
            {{ t('stripe.payouts') }}: {{ status.payouts_enabled ? t('stripe.active') : t('stripe.pending') }}
          </v-chip>
          <v-chip size="small" :color="status.details_submitted ? 'success' : 'default'" variant="tonal">
            {{ t('stripe.details') }}: {{ status.details_submitted ? t('stripe.complete') : t('stripe.open') }}
          </v-chip>
        </div>
        <p v-if="status.stripe_account_id" class="muted small mono">
          {{ t('stripe.account') }}: {{ truncateAccount(status.stripe_account_id) }}
        </p>
        <div class="stripe-actions">
          <v-btn
            color="primary"
            type="button"
            :disabled="busy"
            :loading="busy && busyAction === 'link'"
            @click="startOnboarding"
          >
            {{ status.stripe_account_id && !status.charges_enabled ? t('stripe.continueOnboarding') : t('stripe.connect') }}
          </v-btn>
          <v-btn
            variant="outlined"
            type="button"
            :disabled="busy || !status.stripe_account_id"
            :loading="busy && busyAction === 'refresh'"
            @click="refreshStatus"
          >
            {{ t('stripe.refreshStatus') }}
          </v-btn>
        </div>
        <p v-if="actionMessage" :class="actionMessageType">{{ actionMessage }}</p>
      </template>
    </template>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import HelpLink from './HelpLink.vue'
import {
  createStripeAccountLink,
  fetchStripeConnectStatus,
  refreshStripeConnectStatus,
} from '../utils/stripeConnect'

const { t } = useI18n()

const props = defineProps({
  organisationId: { type: [Number, String], default: null },
})

const status = ref(null)
const loading = ref(false)
const loadError = ref('')
const busy = ref(false)
const busyAction = ref('')
const actionMessage = ref('')
const actionMessageType = ref('')

function truncateAccount(id) {
  const s = String(id || '')
  if (s.length <= 16) return s
  return `${s.slice(0, 10)}…${s.slice(-4)}`
}

async function loadStatus() {
  const id = props.organisationId
  if (!id) {
    status.value = null
    return
  }
  loading.value = true
  loadError.value = ''
  actionMessage.value = ''
  try {
    status.value = await fetchStripeConnectStatus(id)
  } catch (e) {
    status.value = null
    loadError.value = e.message || t('stripe.statusLoadFailed')
  } finally {
    loading.value = false
  }
}

async function startOnboarding() {
  busy.value = true
  busyAction.value = 'link'
  actionMessage.value = ''
  try {
    const result = await createStripeAccountLink(props.organisationId)
    if (result.url) {
      window.location.href = result.url
      return
    }
    actionMessage.value = t('stripe.noOnboardingLink')
    actionMessageType.value = 'error-text'
  } catch (e) {
    actionMessage.value = e.message || t('stripe.onboardingFailed')
    actionMessageType.value = 'error-text'
  } finally {
    busy.value = false
    busyAction.value = ''
  }
}

async function refreshStatus() {
  busy.value = true
  busyAction.value = 'refresh'
  actionMessage.value = ''
  try {
    status.value = { configured: true, ...(await refreshStripeConnectStatus(props.organisationId)) }
    actionMessage.value = t('stripe.statusUpdated')
    actionMessageType.value = 'success-text'
  } catch (e) {
    actionMessage.value = e.message || t('stripe.refreshFailed')
    actionMessageType.value = 'error-text'
  } finally {
    busy.value = false
    busyAction.value = ''
  }
}

watch(() => props.organisationId, loadStatus, { immediate: true })

defineExpose({ loadStatus, refreshStatus })
</script>

<style scoped>
.org-stripe-block {
  margin: 1.25rem 0;
  padding-top: 1rem;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}
.stripe-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.stripe-header-row h3 {
  margin: 0;
}
.stripe-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin: 0.75rem 0;
}
.stripe-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.75rem;
}
.mono {
  font-family: ui-monospace, monospace;
}
.success-text {
  color: var(--vq-success, #22c55e);
  margin-top: 0.5rem;
}
.error-text {
  color: var(--vq-error, #ef4444);
  margin-top: 0.5rem;
}
</style>
