<template>
  <div>
    <h1>Admin</h1>
    <p v-if="needsPin" class="muted">
      6-stelligen Pi Admin-Code eingeben (in der Cloud unter Benutzer hinterlegt, nach Sync gültig).
    </p>
    <p v-else class="muted">Weiterleitung…</p>

    <template v-if="needsPin">
      <PinKeypad ref="keypadRef" @complete="onComplete" />
      <p v-if="error" class="err-text">{{ error }}</p>
      <p v-if="verifying" class="muted">Prüfen…</p>
      <button type="button" class="btn" style="margin-top: 1.5rem; width: 100%" @click="goBack">Abbrechen</button>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as store from '../store'
import PinKeypad from '../components/PinKeypad.vue'

const route = useRoute()
const router = useRouter()
const error = ref('')
const verifying = ref(false)
const keypadRef = ref(null)
const needsPin = computed(() => store.adminRequiresPin())

function redirectAfterUnlock() {
  const redir = route.query.redirect
  if (typeof redir === 'string' && redir.startsWith('/')) {
    router.replace(redir)
  } else {
    router.replace({ name: 'admin' })
  }
}

onMounted(() => {
  if (!store.adminRequiresPin()) {
    store.setAdminUnlocked(true)
    redirectAfterUnlock()
  }
})

async function onComplete(pin) {
  error.value = ''
  verifying.value = true
  try {
    await store.verifyAdminPin(pin)
    redirectAfterUnlock()
  } catch (e) {
    error.value = e.message || 'Ungültiger Code'
    keypadRef.value?.clear()
  } finally {
    verifying.value = false
  }
}

function goBack() {
  router.replace({ name: 'events' })
}
</script>

<style scoped>
.err-text {
  color: var(--danger);
  margin-top: 1rem;
  text-align: center;
}
</style>
