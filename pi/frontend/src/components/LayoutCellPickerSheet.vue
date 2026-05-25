<template>
  <Teleport to="body">
    <div v-if="open" class="sheet-backdrop" @click.self="$emit('close')" />
    <div v-if="open" class="sheet" role="dialog" aria-modal="true">
      <h3>{{ title || 'Position wählen' }}</h3>
      <p class="muted">Antippen zum Hinzufügen</p>
      <ul class="pick-list">
        <li v-for="(item, idx) in items" :key="item.key || idx">
          <button type="button" class="pick-row" @click="$emit('pick', item)">
            <span class="name">{{ item.label }}</span>
            <span v-if="item.priceLabel" class="meta muted">{{ item.priceLabel }}</span>
          </button>
        </li>
      </ul>
      <button type="button" class="btn" style="width: 100%" @click="$emit('close')">Abbrechen</button>
    </div>
  </Teleport>
</template>

<script setup>
defineProps({
  open: Boolean,
  title: { type: String, default: '' },
  items: { type: Array, default: () => [] },
})

defineEmits(['close', 'pick'])
</script>

<style scoped>
.sheet-backdrop {
  z-index: 140;
}
.sheet {
  z-index: 141;
}
.pick-list {
  list-style: none;
  padding: 0;
  margin: 0 0 1rem;
  max-height: 50vh;
  overflow-y: auto;
}
.pick-row {
  width: 100%;
  text-align: left;
  padding: 0.85rem 1rem;
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  background: var(--card);
  color: var(--text);
  margin-bottom: 0.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  cursor: pointer;
  touch-action: manipulation;
}
.pick-row .name {
  font-weight: 600;
}
</style>
