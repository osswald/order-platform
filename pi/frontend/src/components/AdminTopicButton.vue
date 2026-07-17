<template>
  <component
    :is="to ? RouterLink : 'button'"
    :to="to"
    type="button"
    class="admin-topic-btn"
    @click="onClick"
  >
    <span class="admin-topic-icon" aria-hidden="true">
      <slot name="icon" />
    </span>
    <span class="admin-topic-label">{{ label }}</span>
  </component>
</template>

<script setup lang="ts">
import { RouterLink, type RouteLocationRaw } from 'vue-router'

const props = defineProps<{
  label: string
  to?: RouteLocationRaw
}>()

const emit = defineEmits<{
  click: []
}>()

function onClick() {
  if (!props.to) emit('click')
}
</script>

<style scoped>
.admin-topic-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  min-height: 72px;
  padding: 0.85rem 0.5rem;
  border-radius: 0.75rem;
  border: 1px solid var(--border);
  background: var(--card);
  color: var(--text);
  text-decoration: none;
  cursor: pointer;
  font: inherit;
}
.admin-topic-btn:hover {
  border-color: var(--primary);
}
.admin-topic-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.5rem;
  height: 1.5rem;
}
.admin-topic-icon :deep(svg) {
  width: 1.5rem;
  height: 1.5rem;
}
.admin-topic-label {
  font-size: 0.85rem;
  text-align: center;
  line-height: 1.2;
}
</style>
