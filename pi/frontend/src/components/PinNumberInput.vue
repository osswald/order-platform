<template>
  <input
    :value="modelValue"
    type="text"
    inputmode="numeric"
    pattern="[0-9]*"
    :maxlength="maxlength"
    autocomplete="one-time-code"
    class="input"
    @input="onInput"
    @keydown="onKeydown"
  />
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    modelValue?: string
    maxlength?: number
  }>(),
  { modelValue: '', maxlength: 12 },
)

const emit = defineEmits<{
  'update:modelValue': [value: string]
  submit: []
}>()

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter') {
    event.preventDefault()
    emit('submit')
  }
}

function onInput(event: Event) {
  const target = event.target as HTMLInputElement
  const max = Number(target.getAttribute('maxlength') || 12)
  const digits = String(target.value || '').replace(/\D/g, '').slice(0, max)
  target.value = digits
  emit('update:modelValue', digits)
}
</script>

<style scoped>
.input {
  font-variant-numeric: tabular-nums;
}
</style>
