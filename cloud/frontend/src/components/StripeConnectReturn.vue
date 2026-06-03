<template>
  <section class="stripe-return-panel">
    <v-card max-width="32rem">
      <v-card-title>{{ title }}</v-card-title>
      <v-card-text>
        <p v-if="busy" class="muted">Bitte warten…</p>
        <p v-else-if="error" class="error-text">{{ error }}</p>
        <p v-else>{{ message }}</p>
      </v-card-text>
      <v-card-actions v-if="!busy">
        <v-btn color="primary" :to="{ name: 'organisations' }">Zu Organisationen</v-btn>
      </v-card-actions>
    </v-card>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { createStripeAccountLink, refreshStripeConnectStatus } from '../utils/stripeConnect'

const route = useRoute()
const busy = ref(true)
const error = ref('')
const message = ref('')

const isRefreshRoute = computed(() => route.name === 'stripe-connect-refresh')
const title = computed(() =>
  isRefreshRoute.value ? 'Stripe Onboarding' : 'Stripe verbunden',
)

function resolveOrganisationId() {
  const q = route.query.organisation_id
  if (q != null && String(q).trim() !== '') return Number(q)
  const stored = localStorage.getItem('active_organisation_id')
  if (stored) return Number(stored)
  return null
}

onMounted(async () => {
  const orgId = resolveOrganisationId()
  if (!orgId || Number.isNaN(orgId)) {
    busy.value = false
    error.value = 'Keine Organisation ausgewählt. Bitte in Organisationen erneut starten.'
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
      message.value = 'Onboarding-Status aktualisiert.'
    } else {
      await refreshStripeConnectStatus(orgId)
      message.value = 'Stripe-Konto wurde aktualisiert. Sie können nun Kartenzahlungen in Veranstaltungen aktivieren.'
    }
  } catch (e) {
    error.value = e.message || 'Stripe-Rückkehr fehlgeschlagen.'
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
