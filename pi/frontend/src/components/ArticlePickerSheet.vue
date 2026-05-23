<template>
  <Teleport to="body">
    <div v-if="open" class="sheet-backdrop" @click.self="$emit('close')" />
    <div v-if="open" class="sheet" role="dialog" aria-modal="true">
      <h3>Artikel wählen</h3>
      <button
        v-for="a in articles"
        :key="a.id"
        type="button"
        class="article-btn"
        @click="pick(a.id)"
      >
        {{ a.name || a.label }}
      </button>
      <button type="button" class="btn" style="width: 100%; margin-top: 0.75rem" @click="$emit('close')">
        Schließen
      </button>
    </div>
  </Teleport>
</template>

<script setup>
const props = defineProps({
  open: Boolean,
  articles: { type: Array, default: () => [] },
})

const emit = defineEmits(['close', 'add'])

function pick(article_id) {
  emit('add', { article_id, qty: 1 })
}
</script>

<style scoped>
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
.article-btn:active {
  background: var(--accent);
  color: #fff;
}
</style>
