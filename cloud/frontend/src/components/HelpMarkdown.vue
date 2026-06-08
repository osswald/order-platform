<template>
  <div class="vq-prose" v-html="html" />
</template>

<script setup>
defineProps({
  html: {
    type: String,
    default: '',
  },
})
</script>
