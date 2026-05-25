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

<script setup>
defineProps({
  modelValue: { type: String, default: '' },
  maxlength: { type: Number, default: 12 },
})

const emit = defineEmits(['update:modelValue', 'submit'])

function onKeydown(event) {
  if (event.key === 'Enter') {
    event.preventDefault()
    emit('submit')
  }
}

function onInput(event) {
  const max = Number(event.target.getAttribute('maxlength') || 12)
  const digits = String(event.target.value || '').replace(/\D/g, '').slice(0, max)
  event.target.value = digits
  emit('update:modelValue', digits)
}
</script>

<style scoped>
.input {
  font-variant-numeric: tabular-nums;
}
</style>
