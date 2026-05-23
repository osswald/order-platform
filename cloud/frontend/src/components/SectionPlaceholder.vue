<template>
  <section class="placeholder-panel">
    <div class="placeholder-card">
      <div class="placeholder-icon">⚙️</div>
      <div>
        <h2>{{ title }}</h2>
        <p>{{ description }}</p>
      </div>
    </div>
  </section>
</template>

<script setup>
import { defineProps } from 'vue'

const props = defineProps({
  title: {
    type: String,
    default: 'Bereich in Arbeit',
  },
  description: {
    type: String,
    default:
      'Diese Sektion ist bereits geplant und wird in Kürze mit Echtzeitdaten aus dem Vendiqo ERP erweitert.',
  },
})
</script>

<style scoped>
.placeholder-panel {
  padding: 2rem;
  min-height: 100%;
  background: var(--p-surface-ground);
}

.placeholder-card {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  padding: 2rem;
  border-radius: 1rem;
  background: var(--p-surface-card);
  border: 1px solid var(--p-content-border-color);
  box-shadow: var(--p-card-shadow);
}

.placeholder-icon {
  display: grid;
  place-items: center;
  width: 4rem;
  height: 4rem;
  font-size: 2rem;
  border-radius: 1rem;
  background: var(--p-primary-50);
  color: var(--p-primary-color);
}

h2 {
  margin: 0 0 0.5rem;
  color: var(--p-text-color);
}
p {
  margin: 0;
  color: var(--p-text-muted-color);
}
</style>
