<template>
  <div>
    <h1>Kellner</h1>
    <p class="muted">{{ event?.name }}</p>
    <div v-if="!waiters.length" class="card">
      <p>Keine Kellner in der Event-Konfiguration.</p>
    </div>
    <template v-else>
      <div class="card">
        <div class="field">
          <label>Kellner</label>
          <select v-model.number="waiterId" class="select">
            <option v-for="w in waiters" :key="w.uuid" :value="w.uuid">{{ w.name }}</option>
          </select>
        </div>
        <div class="field">
          <label>PIN</label>
          <input v-model="pin" type="password" class="input" maxlength="12" autocomplete="one-time-code" />
        </div>
        <button type="button" class="btn primary" @click="login">Anmelden</button>
        <p v-if="err" class="muted" style="color: var(--danger)">{{ err }}</p>
      </div>
    </template>
    <p class="muted">
      <RouterLink :to="{ name: 'events' }">Anderes Event</RouterLink>
      ·
      <RouterLink :to="{ name: 'hub' }">Hub</RouterLink>
    </p>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import * as store from '../store'

const router = useRouter()
const route = useRoute()
const event = computed(() => store.selectedEvent.value)
const waiters = computed(() => event.value?.configuration?.event_waiters || [])
const waiterId = ref(null)
const pin = ref('')
const err = ref('')

watch(
  waiters,
  (ws) => {
    if (ws.length && waiterId.value == null) waiterId.value = ws[0].uuid
  },
  { immediate: true },
)

function login() {
  err.value = ''
  const w = waiters.value.find((x) => x.uuid === waiterId.value)
  if (!w) {
    err.value = 'Kellner wählen.'
    return
  }
  if (w.pin !== pin.value) {
    err.value = 'PIN ungültig.'
    return
  }
  store.setWaiter({ uuid: w.uuid, name: w.name })
  const redir = route.query.redirect
  if (typeof redir === 'string' && redir.startsWith('/')) {
    router.replace(redir)
  } else {
    router.replace({ name: 'hub' })
  }
}
</script>
