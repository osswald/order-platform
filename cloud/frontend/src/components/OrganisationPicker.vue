<template>
  <div ref="rootEl" class="organisation-picker">
    <div v-if="selectedOrgs.length" class="selected-list">
      <span v-for="o in selectedOrgs" :key="o.id" class="chip">
        {{ displayOrg(o) }}
        <button type="button" class="remove" aria-label="Entfernen" @click="remove(o.id)">&times;</button>
      </span>
    </div>

    <div class="input-wrap">
      <input
        ref="inputRef"
        v-model="term"
        type="text"
        class="picker-input"
        autocomplete="off"
        placeholder="Organisation suchen oder aus Liste wählen…"
        @focus="onFocus"
        @input="onInput"
        @keydown.escape.prevent="closeDropdown"
      />
      <div v-if="loading" class="loader" aria-hidden="true">…</div>
    </div>

    <ul v-show="dropdownOpen" class="results" role="listbox">
      <template v-if="loading">
        <li class="result-hint">Wird geladen…</li>
      </template>
      <template v-else-if="!filteredChoices.length">
        <li class="result-hint">
          {{
            directory.length
              ? 'Keine weiteren Organisationen für diese Suche.'
              : 'Keine Organisationen geladen.'
          }}
        </li>
      </template>
      <template v-else>
        <li v-for="r in filteredChoices" :key="r.id" class="result-item">
          <button type="button" @click="add(r)">{{ displayOrg(r) }}</button>
        </li>
      </template>
    </ul>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { apiFetch } from '../api'

const props = defineProps({
  modelValue: {
    type: Array,
    default: () => [],
  },
})
const emit = defineEmits(['update:modelValue'])

const rootEl = ref(null)
const inputRef = ref(null)
const term = ref('')
const loading = ref(false)
const dropdownOpen = ref(false)
const directory = ref([])
const selectedOrgs = ref([])

let inFlightFetch = null

function displayOrg(o) {
  const name = o.name || `Organisation #${o.id}`
  if (o.country) {
    return `${name} (${o.country})`
  }
  return name
}

const selectedIdSet = computed(() => new Set((props.modelValue || []).map((x) => Number(x))))

const filteredChoices = computed(() => {
  const q = term.value.trim().toLowerCase()
  return directory.value.filter((o) => {
    if (selectedIdSet.value.has(Number(o.id))) return false
    if (!q) return true
    const name = (o.name || '').toLowerCase()
    const country = (o.country || '').toLowerCase()
    const city = (o.city || '').toLowerCase()
    return (
      name.includes(q) ||
      country.includes(q) ||
      city.includes(q) ||
      String(o.id).includes(q)
    )
  })
})

async function fetchDirectory() {
  if (inFlightFetch) return inFlightFetch
  loading.value = true
  inFlightFetch = (async () => {
    try {
      const resp = await apiFetch('/organisations/')
      if (resp.ok) {
        directory.value = await resp.json()
      } else {
        directory.value = []
      }
    } catch (e) {
      directory.value = []
    } finally {
      loading.value = false
      inFlightFetch = null
    }
  })()
  return inFlightFetch
}

function syncSelectedFromModel() {
  const ids = props.modelValue || []
  const map = new Map(directory.value.map((o) => [Number(o.id), o]))
  selectedOrgs.value = ids.map((raw) => {
    const id = Number(raw)
    return (
      map.get(id) ||
      selectedOrgs.value.find((s) => Number(s.id) === id) ||
      { id }
    )
  })
}

watch(
  () => props.modelValue,
  async () => {
    if (!directory.value.length) {
      await fetchDirectory()
    }
    syncSelectedFromModel()
  },
  { immediate: true, deep: true }
)

watch(directory, () => {
  syncSelectedFromModel()
})

function onFocus() {
  dropdownOpen.value = true
  fetchDirectory()
}

function onInput() {
  dropdownOpen.value = true
}

function closeDropdown() {
  dropdownOpen.value = false
}

function add(o) {
  const prev = (props.modelValue || []).map((x) => Number(x))
  const id = Number(o.id)
  if (prev.includes(id)) return
  const ids = [...prev, id]
  emit('update:modelValue', ids)
  selectedOrgs.value = [...selectedOrgs.value.filter((s) => Number(s.id) !== id), o]
  term.value = ''
  inputRef.value?.focus()
}

function remove(id) {
  const n = Number(id)
  const ids = (props.modelValue || []).filter((x) => Number(x) !== n)
  emit('update:modelValue', ids)
}

function onDocPointerDown(e) {
  if (!dropdownOpen.value) return
  const el = rootEl.value
  if (el && !el.contains(e.target)) {
    closeDropdown()
  }
}

onMounted(() => {
  document.addEventListener('pointerdown', onDocPointerDown, true)
})

onUnmounted(() => {
  document.removeEventListener('pointerdown', onDocPointerDown, true)
})
</script>

<style scoped>
.organisation-picker {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.selected-list {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem 0.65rem;
  border-radius: var(--p-border-radius-md);
  background: var(--p-surface-100);
  border: 1px solid var(--p-content-border-color);
  font-size: 0.92rem;
  color: var(--p-text-color);
}

.chip .remove {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  min-width: 1.35rem;
  height: 1.35rem;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--p-text-muted-color);
  font-weight: 700;
  font-size: 1.1rem;
  line-height: 1;
  cursor: pointer;
}

.chip .remove:hover {
  background: var(--p-red-50);
  color: var(--p-red-600);
}

.input-wrap {
  position: relative;
  display: flex;
  align-items: center;
}

.picker-input {
  flex: 1;
  width: 100%;
  border: 1px solid var(--p-form-field-border-color);
  border-radius: var(--p-form-field-border-radius);
  padding: 0.95rem 1rem;
  background: var(--p-form-field-background);
  color: var(--p-form-field-color);
  font-size: 0.95rem;
  font-family: inherit;
}

.picker-input::placeholder {
  color: var(--p-form-field-placeholder-color);
}

.picker-input:focus {
  outline: none;
  border-color: var(--p-form-field-focus-border-color);
  box-shadow: var(--p-form-field-focus-ring-shadow);
}

.loader {
  position: absolute;
  right: 0.85rem;
  font-size: 0.95rem;
  opacity: 0.55;
  pointer-events: none;
}

.results {
  position: absolute;
  left: 0;
  right: 0;
  top: 100%;
  z-index: 40;
  margin: 0.25rem 0 0;
  padding: 0.35rem 0;
  list-style: none;
  max-height: 14rem;
  overflow-y: auto;
  border-radius: 10px;
  border: 1px solid var(--p-content-border-color);
  background: var(--p-overlay-popover-background);
  box-shadow: var(--p-overlay-popover-shadow);
}

.result-hint {
  padding: 0.65rem 1rem;
  font-size: 0.88rem;
  color: var(--p-text-muted-color);
}

.result-item button {
  width: 100%;
  text-align: left;
  padding: 0.65rem 1rem;
  border: none;
  background: transparent;
  color: var(--p-text-color);
  font-size: 0.95rem;
  font-family: inherit;
  cursor: pointer;
}

.result-item button:hover {
  background: var(--p-surface-hover);
}

.result-item button:focus-visible {
  outline: 2px solid var(--p-primary-color);
  outline-offset: -2px;
}
</style>
