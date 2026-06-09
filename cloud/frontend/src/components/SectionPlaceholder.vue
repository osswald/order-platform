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
import { i18n } from '../i18n'

defineProps({
  title: {
    type: String,
    default: () => i18n.global.t('layout.placeholder.title'),
  },
  description: {
    type: String,
    default: () => i18n.global.t('layout.placeholder.description'),
  },
})
</script>

<style scoped>
.placeholder-panel {
  padding: 2rem;
  min-height: 100%;
  background: rgb(var(--v-theme-background));
}

.placeholder-card {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  padding: 2rem;
  border-radius: 1rem;
  background: rgb(var(--v-theme-surface));
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.placeholder-icon {
  display: grid;
  place-items: center;
  width: 4rem;
  height: 4rem;
  font-size: 2rem;
  border-radius: 1rem;
  background: rgba(var(--v-theme-primary), 0.12);
  color: rgb(var(--v-theme-primary));
}

h2 {
  margin: 0 0 0.5rem;
}
p {
  margin: 0;
  opacity: 0.7;
}
</style>
