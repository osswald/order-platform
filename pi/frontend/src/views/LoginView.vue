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
          <button
            type="button"
            class="waiter-picker"
            :aria-expanded="waiterListOpen"
            @click="toggleWaiterList"
          >
            <span class="waiter-picker-main">
              <span class="waiter-picker-name">{{ selectedWaiter?.name || 'Kellner wählen' }}</span>
              <span class="waiter-picker-hint muted">{{ waiterListOpen ? 'Schließen' : 'Tippen zum Wechseln' }}</span>
            </span>
            <span class="waiter-picker-chevron" aria-hidden="true">{{ waiterListOpen ? '▲' : '▼' }}</span>
          </button>
          <ul v-if="waiterListOpen" class="waiter-list">
            <li v-for="w in waiters" :key="w.uuid">
              <button
                type="button"
                class="waiter-row"
                :class="{ 'waiter-row--selected': w.uuid === waiterId }"
                @click="pickWaiter(w.uuid)"
              >
                <span class="waiter-row-name">{{ w.name }}</span>
                <span v-if="w.uuid === waiterId" class="waiter-row-check" aria-hidden="true">✓</span>
              </button>
            </li>
          </ul>
        </div>
        <div class="field">
          <label>PIN</label>
          <input v-model="pin" type="password" class="input" maxlength="12" autocomplete="one-time-code" />
        </div>
        <button type="button" class="btn primary" @click="login">Anmelden</button>
        <p v-if="err" class="err-msg">{{ err }}</p>
      </div>
    </template>
    <p class="muted footer-links">
      <RouterLink :to="{ name: 'events' }">Anderes Event</RouterLink>
      ·
      <RouterLink :to="{ name: 'hub' }">Hub</RouterLink>
    </p>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useWaiterSession } from '../composables/useWaiterSession'

const router = useRouter()
const route = useRoute()
const { selectedEvent, setWaiter } = useWaiterSession()
const event = selectedEvent
const waiters = computed(() => event.value?.configuration?.event_waiters || [])
const waiterId = ref(null)
const waiterListOpen = ref(false)
const pin = ref('')
const err = ref('')

const selectedWaiter = computed(() => waiters.value.find((x) => x.uuid === waiterId.value) || null)

watch(
  waiters,
  (ws) => {
    if (ws.length && waiterId.value == null) waiterId.value = ws[0].uuid
  },
  { immediate: true },
)

function toggleWaiterList() {
  waiterListOpen.value = !waiterListOpen.value
}

function pickWaiter(uuid) {
  waiterId.value = uuid
  waiterListOpen.value = false
}

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
  setWaiter({ uuid: w.uuid, name: w.name })
  const redir = route.query.redirect
  if (typeof redir === 'string' && redir.startsWith('/')) {
    router.replace(redir)
  } else {
    router.replace({ name: 'hub' })
  }
}
</script>

<style scoped>
.field {
  margin-bottom: 1rem;
}

label {
  display: block;
  margin-bottom: 0.35rem;
  font-size: 0.875rem;
  font-weight: 600;
}

.waiter-picker {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.85rem 1rem;
  border-radius: 0.75rem;
  border: 1px solid var(--border);
  background: var(--card);
  color: var(--text);
  cursor: pointer;
  min-height: 56px;
  text-align: left;
}

.waiter-picker-main {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  min-width: 0;
}

.waiter-picker-name {
  font-weight: 600;
  font-size: 1.1rem;
}

.waiter-picker-hint {
  font-size: 0.85rem;
}

.waiter-picker-chevron {
  flex-shrink: 0;
  font-size: 0.75rem;
  opacity: 0.7;
}

.waiter-list {
  list-style: none;
  padding: 0;
  margin: 0.5rem 0 0;
}

.waiter-list li {
  margin-bottom: 0.5rem;
}

.waiter-list li:last-child {
  margin-bottom: 0;
}

.waiter-row {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.85rem 1rem;
  border-radius: 0.75rem;
  border: 1px solid var(--border);
  background: var(--bg, var(--card));
  color: var(--text);
  cursor: pointer;
  min-height: 52px;
  text-align: left;
}

.waiter-row--selected {
  border-color: var(--accent, #ea580c);
  background: var(--card);
}

.waiter-row-name {
  font-weight: 600;
  font-size: 1.05rem;
}

.waiter-row-check {
  color: var(--accent, #ea580c);
  font-weight: 700;
}

.err-msg {
  margin: 0.75rem 0 0;
  color: var(--danger);
  font-size: 0.9rem;
}

.footer-links {
  margin-top: 1rem;
}
</style>
