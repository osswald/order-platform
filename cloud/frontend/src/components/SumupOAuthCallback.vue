<template>
  <section class="sumup-oauth-callback">
    <v-card max-width="32rem">
      <v-card-title>{{ $t('sumupDevices.oauthCallbackTitle') }}</v-card-title>
      <v-card-text>
        <p class="muted">{{ $t('sumupDevices.pleaseWait') }}</p>
      </v-card-text>
    </v-card>
  </section>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { apiBaseUrl } from '../api'

const route = useRoute()
const router = useRouter()

onMounted(() => {
  const code = route.query.code
  const state = route.query.state
  // If SumUp is configured to redirect to the SPA, forward the code to the API callback.
  if (typeof code === 'string' && code.trim() && typeof state === 'string' && state.trim()) {
    const url = new URL(`${apiBaseUrl()}/sumup/oauth/callback`)
    url.searchParams.set('code', code)
    url.searchParams.set('state', state)
    window.location.replace(url.toString())
    return
  }

  const query: Record<string, string> = {}
  if (route.query.connected != null) {
    query.connected = String(route.query.connected)
  }
  if (route.query.error != null) {
    query.error = String(route.query.error)
  }
  void router.replace({
    name: 'sumup-devices',
    query,
  })
})
</script>

<style scoped>
.sumup-oauth-callback {
  padding: 2rem 1rem;
}
</style>
