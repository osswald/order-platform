<template>
  <section class="stripe-return-panel">
    <v-card max-width="32rem">
      <v-card-title>{{ title }}</v-card-title>
      <v-card-text>
        <p v-if="busy" class="muted">{{ $t('stripe.pleaseWait') }}</p>
        <p v-else-if="error" class="error-text">{{ error }}</p>
        <p v-else>{{ message }}</p>
      </v-card-text>
      <v-card-actions v-if="!busy">
        <v-btn color="primary" :to="{ name: 'organisations' }">{{ $t('stripe.toOrganisations') }}</v-btn>
      </v-card-actions>
    </v-card>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { createStripeAccountLink, refreshStripeConnectStatus } from '../utils/stripeConnect'
import { getErrorMessage } from '@/types/api'
import { normalizeOrganisationId } from '@/utils/orgId'

const { t } = useI18n()
const route = useRoute()
const busy = ref(true)
const error = ref('')
const message = ref('')

const isRefreshRoute = computed(() => route.name === 'stripe-connect-refresh')
const title = computed(() =>
  isRefreshRoute.value ? t('stripe.onboardingTitle') : t('stripe.connectedTitle'),
)

function resolveOrganisationId() {
  return normalizeOrganisationId(localStorage.getItem('active_organisation_id'))
}

onMounted(async () => {
  const orgId = resolveOrganisationId()
  if (orgId == null) {
    busy.value = false
    error.value = t('stripe.noOrganisation')
    return
  }
  try {
    if (isRefreshRoute.value) {
      const status = await refreshStripeConnectStatus(orgId)
      if (!status.charges_enabled && status.stripe_account_id) {
        const link = await createStripeAccountLink(orgId)
        if (link.url) {
          window.location.href = link.url
          return
        }
      }
      message.value = t('stripe.onboardingUpdated')
    } else {
      await refreshStripeConnectStatus(orgId)
      message.value = t('stripe.accountUpdated')
    }
  } catch (e: unknown) {
    error.value = getErrorMessage(e, t('stripe.returnFailed'))
  } finally {
    busy.value = false
  }
})
</script>

<style scoped>
.stripe-return-panel {
  padding: 2rem 1rem;
}
.error-text {
  color: var(--vq-error, #ef4444);
}
</style>
