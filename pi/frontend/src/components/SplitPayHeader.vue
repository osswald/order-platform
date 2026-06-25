<template>
  <header class="split-header">
    <button type="button" class="header-btn" aria-label="Zurück" @click="$emit('back')">←</button>
    <h1 class="split-title">{{ title || `Offene Posten Tisch: ${table}` }}</h1>
    <slot name="actions">
      <button type="button" class="header-btn menu" aria-label="Menü" @click="$emit('menu')">☰</button>
    </slot>
  </header>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    table?: number | string
    title?: string
  }>(),
  { table: '', title: '' },
)

defineEmits<{
  back: []
  menu: []
}>()
</script>

<style scoped>
.split-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: var(--accent, #ea580c);
  color: #fff;
  padding: 0.65rem 0.5rem;
  flex-shrink: 0;
}
.split-title {
  flex: 1;
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  text-align: center;
}
.header-btn {
  min-width: 44px;
  min-height: 44px;
  border: none;
  background: transparent;
  color: inherit;
  font-size: 1.25rem;
  cursor: pointer;
}
.header-btn:disabled {
  opacity: 0.4;
}
</style>
