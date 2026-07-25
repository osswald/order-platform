<template>
  <Teleport to="body">
    <div v-if="open" class="sheet-backdrop" @click.self="onCancel" />
    <div
      v-if="open"
      class="sheet"
      role="dialog"
      aria-modal="true"
      :style="sheetStyle"
    >
      <header class="sheet-header">
        <h3>Neue Sammelrechnung</h3>
        <button type="button" class="link-back" @click="onCancel">← Zurück</button>
      </header>
      <label class="field-label">Name</label>
      <input
        ref="inputEl"
        v-model="name"
        type="text"
        class="text-input"
        maxlength="128"
        placeholder="z. B. Personal"
        @input="onNameInput"
        @compositionend="onNameInput"
        @keydown.enter.prevent="submit"
      />
      <button
        type="button"
        class="btn primary confirm-btn"
        :disabled="!canConfirm"
        @click="submit"
      >
        {{ confirmLabel }}
      </button>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useKeyboardBottomInset } from '@/composables/useKeyboardBottomInset'

const props = withDefaults(
  defineProps<{
    open?: boolean
    busy?: boolean
    confirmLabel?: string
    initialName?: string
  }>(),
  {
    open: false,
    busy: false,
    confirmLabel: 'Erstellen',
    initialName: '',
  },
)

const emit = defineEmits<{
  close: []
  confirm: [name: string]
}>()

const name = ref('')
const inputEl = ref<HTMLInputElement | null>(null)
const keyboardBottomInset = useKeyboardBottomInset()

const sheetStyle = computed(() => ({
  '--keyboard-bottom': `${keyboardBottomInset.value}px`,
}))

/** Prefer live input value so Android IME composition still enables the CTA. */
const canConfirm = computed(() => {
  if (props.busy) return false
  const live = inputEl.value?.value ?? name.value
  return Boolean(live.trim())
})

watch(
  () => props.open,
  async (v) => {
    if (v) {
      name.value = props.initialName
      await nextTick()
      inputEl.value?.focus()
    }
  },
)

function onNameInput(ev: Event) {
  const t = ev.target
  if (t instanceof HTMLInputElement) {
    name.value = t.value
  }
}

function onCancel() {
  emit('close')
}

function submit() {
  const trimmed = (inputEl.value?.value ?? name.value).trim()
  if (!trimmed || props.busy) return
  name.value = trimmed
  emit('confirm', trimmed)
}
</script>

<style scoped>
.sheet-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  z-index: 150;
}
.sheet {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 151;
  background: var(--card);
  border-radius: 1rem 1rem 0 0;
  padding: 1rem 1rem calc(1rem + var(--safe-bottom) + var(--keyboard-bottom, 0px));
  max-height: 85vh;
  overflow-y: auto;
}
.sheet-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}
.sheet-header h3 {
  margin: 0;
}
.link-back {
  border: none;
  background: none;
  color: var(--primary);
  font-size: 0.95rem;
  cursor: pointer;
}
.field-label {
  display: block;
  margin-bottom: 0.35rem;
  font-size: 0.9rem;
}
.text-input {
  width: 100%;
  padding: 0.65rem 0.75rem;
  border-radius: 0.5rem;
  border: 1px solid var(--border);
  font-size: 1rem;
}
.confirm-btn {
  width: 100%;
  margin-top: 1rem;
}
</style>
