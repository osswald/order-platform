<template>
  <label class="vq-label" :class="{ 'vq-label--required': required }">
    <slot>{{ text }}</slot>
  </label>
</template>

<script setup lang="ts">
defineProps({
  text: { type: String, default: '' },
  required: { type: Boolean, default: false },
})
</script>
