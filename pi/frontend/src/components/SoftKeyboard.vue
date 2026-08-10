<template>
  <div class="soft-keyboard" role="group" aria-label="Tastatur">
    <div v-for="(row, ri) in rows" :key="ri" class="kb-row">
      <button
        v-for="key in row"
        :key="`${ri}-${key}`"
        type="button"
        class="kb-key"
        :class="{ wide: key === 'space' || key === '⌫' }"
        @click="onKey(key)"
      >
        {{ labelFor(key) }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    modelValue?: string
    maxlength?: number
  }>(),
  { modelValue: '', maxlength: 512 },
)

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const value = ref(props.modelValue ?? '')
const shifted = ref(false)

watch(
  () => props.modelValue,
  (v) => {
    if (v !== undefined && v !== value.value) value.value = v
  },
)

const baseRows = [
  ['q', 'w', 'e', 'r', 't', 'z', 'u', 'i', 'o', 'p'],
  ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l'],
  ['⇧', 'y', 'x', 'c', 'v', 'b', 'n', 'm', '⌫'],
  ['ä', 'ö', 'ü', 'ß', 'space'],
]

const rows = computed(() =>
  baseRows.map((row) =>
    row.map((k) => {
      if (k === '⇧' || k === '⌫' || k === 'space' || k === 'ß') return k
      if (shifted.value) {
        if (k === 'ä') return 'Ä'
        if (k === 'ö') return 'Ö'
        if (k === 'ü') return 'Ü'
        return k.toUpperCase()
      }
      return k
    }),
  ),
)

function labelFor(key: string): string {
  if (key === 'space') return 'Leer'
  return key
}

function setValue(next: string) {
  value.value = next
  emit('update:modelValue', next)
}

function onKey(key: string) {
  if (key === '⇧') {
    shifted.value = !shifted.value
    return
  }
  if (key === '⌫') {
    setValue(value.value.slice(0, -1))
    return
  }
  const ch = key === 'space' ? ' ' : key
  if (value.value.length >= props.maxlength) return
  setValue(value.value + ch)
  if (shifted.value) shifted.value = false
}
</script>

<style scoped>
.soft-keyboard {
  margin-top: 0.75rem;
  user-select: none;
}
.kb-row {
  display: flex;
  gap: 0.25rem;
  margin-bottom: 0.25rem;
  justify-content: center;
}
.kb-key {
  flex: 1;
  min-height: 42px;
  max-width: 2.5rem;
  border-radius: 0.4rem;
  border: 1px solid var(--border);
  background: var(--card);
  color: var(--text);
  font-size: 1rem;
  cursor: pointer;
  touch-action: manipulation;
}
.kb-key.wide {
  max-width: none;
  flex: 2.5;
}
</style>
