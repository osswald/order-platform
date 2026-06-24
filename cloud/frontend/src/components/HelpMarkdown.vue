<template>
  <div class="vq-prose" v-html="html" />
</template>

<script setup lang="ts">
defineProps({
  html: {
    type: String,
    default: '',
  },
})
</script>
