<template>
  <Teleport to="body">
    <div v-if="open" class="sheet-backdrop" @click.self="$emit('close')" />
    <div v-if="open" class="sheet sheet--picker" role="dialog" aria-modal="true">
      <header class="sheet-header">
        <h3>Artikel wählen</h3>
      </header>
      <SheetScrollBody :active="open">
        <button
          v-for="a in articles"
          :key="a.id"
          type="button"
          class="article-btn"
          @click="pick(a.id)"
        >
          {{ a.name || a.label }}
        </button>
      </SheetScrollBody>
      <div class="sheet__footer">
        <button type="button" class="btn" @click="$emit('close')">Schließen</button>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import SheetScrollBody from './SheetScrollBody.vue'

defineProps({
  open: Boolean,
  articles: { type: Array, default: () => [] },
})

const emit = defineEmits(['close', 'add'])

function pick(article_id) {
  emit('add', { article_id, qty: 1 })
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
  padding: 1rem 1rem calc(1rem + var(--safe-bottom));
  border-top: 1px solid var(--border);
}
.sheet-header h3 {
  margin: 0;
}
.article-btn {
  width: 100%;
  text-align: left;
  padding: 0.85rem 1rem;
  margin-bottom: 0.5rem;
  border-radius: 0.5rem;
  border: 1px solid var(--border);
  background: var(--card);
  color: var(--text);
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  touch-action: manipulation;
}
.article-btn:last-child {
  margin-bottom: 0;
}
.article-btn:active {
  background: var(--accent);
  color: #fff;
}
.sheet__footer .btn {
  width: 100%;
  min-height: 48px;
  touch-action: manipulation;
}
</style>
