<template>
  <div>
    <h1>Kasse</h1>
    <p class="muted">{{ event?.name }}</p>

    <div v-if="!registers.length" class="card">
      <p>Für dieses Event sind keine Kassen konfiguriert.</p>
    </div>
    <template v-else>
      <div class="card">
        <div class="field">
          <label>Kasse</label>
          <button
            type="button"
            class="picker-btn"
            :aria-expanded="registerListOpen"
            @click="toggleRegisterList"
          >
            <span class="picker-main">
              <span class="picker-name">{{ selectedRegister?.name || 'Kasse wählen' }}</span>
              <span class="picker-hint muted">{{ registerListOpen ? 'Schließen' : 'Tippen zum Wechseln' }}</span>
            </span>
            <span class="picker-chevron" aria-hidden="true">{{ registerListOpen ? '▲' : '▼' }}</span>
          </button>
          <ul v-if="registerListOpen" class="picker-list">
            <li v-for="reg in registers" :key="reg.uuid">
              <button
                type="button"
                class="picker-row"
                :class="{ 'picker-row--selected': reg.uuid === registerId }"
                @click="pickRegister(reg.uuid)"
              >
                <span class="picker-row-name">{{ reg.name }}</span>
                <span v-if="reg.uuid === registerId" class="picker-row-check" aria-hidden="true">✓</span>
              </button>
            </li>
          </ul>
        </div>
        <div class="field">
          <label>PIN</label>
          <input
            v-model="pin"
            type="password"
            class="input"
            maxlength="4"
            inputmode="numeric"
            autocomplete="one-time-code"
          />
        </div>
        <button type="button" class="btn primary" @click="login">Anmelden</button>
        <p v-if="err" class="err-msg">{{ err }}</p>
      </div>
    </template>

    <footer class="screen-footer">
      <button type="button" class="btn" @click="router.push({ name: 'events' })">Anderes Event</button>
      <button type="button" class="btn" @click="router.push({ name: 'event-mode' })">Modus wechseln</button>
    </footer>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useEventContext } from '../composables/useEventContext'
import { useRegisterSession } from '../composables/useRegisterSession'
import { setWaiter } from '../store'

const router = useRouter()
const route = useRoute()
const { event } = useEventContext()
const { setRegisterSession } = useRegisterSession()

const registers = computed(() =>
  (event.value?.configuration?.cash_registers || []).slice().sort((a, b) => {
    const so = (Number(a.sort_order) || 0) - (Number(b.sort_order) || 0)
    return so || String(a.name || '').localeCompare(String(b.name || ''))
  }),
)

const registerId = ref(null)
const registerListOpen = ref(false)
const pin = ref('')
const err = ref('')

const selectedRegister = computed(() => registers.value.find((x) => x.uuid === registerId.value) || null)

watch(
  registers,
  (regs) => {
    if (regs.length && registerId.value == null) registerId.value = regs[0].uuid
  },
  { immediate: true },
)

function toggleRegisterList() {
  registerListOpen.value = !registerListOpen.value
}

function pickRegister(uuid) {
  registerId.value = uuid
  registerListOpen.value = false
}

function login() {
  err.value = ''
  const reg = registers.value.find((x) => x.uuid === registerId.value)
  if (!reg) {
    err.value = 'Kasse wählen.'
    return
  }
  const expectedPin = reg.pin ?? '0000'
  if (expectedPin !== pin.value) {
    err.value = 'PIN ungültig.'
    return
  }
  setWaiter(null)
  setRegisterSession({ uuid: reg.uuid, name: reg.name })
  const redir = route.query.redirect
  if (typeof redir === 'string' && redir.startsWith('/')) {
    router.replace(redir)
  } else {
    router.replace({ name: 'register-hub', params: { registerUuid: reg.uuid }, query: { fresh: '1' } })
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

.picker-btn {
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

.picker-main {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  min-width: 0;
}

.picker-name {
  font-weight: 600;
  font-size: 1.1rem;
}

.picker-hint {
  font-size: 0.85rem;
}

.picker-chevron {
  flex-shrink: 0;
  font-size: 0.75rem;
  opacity: 0.7;
}

.picker-list {
  list-style: none;
  padding: 0;
  margin: 0.5rem 0 0;
}

.picker-list li {
  margin-bottom: 0.5rem;
}

.picker-list li:last-child {
  margin-bottom: 0;
}

.picker-row {
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

.picker-row--selected {
  border-color: var(--accent, #ea580c);
  background: var(--card);
}

.picker-row-name {
  font-weight: 600;
  font-size: 1.05rem;
}

.picker-row-check {
  color: var(--accent, #ea580c);
  font-weight: 700;
}

.err-msg {
  margin: 0.75rem 0 0;
  color: var(--danger);
  font-size: 0.9rem;
}
</style>
