<template>
  <Teleport to="body">
    <div v-if="open" class="sheet-backdrop" @click.self="$emit('close')" />
    <div v-if="open" class="sheet" role="dialog" aria-modal="true">
      <header class="sheet-header">
        <h3>{{ title || 'Position wählen' }}</h3>
        <p class="muted">Antippen zum Hinzufügen</p>
      </header>
      <SheetOptionList :items="items" max-height="50vh" @pick="$emit('pick', $event)" />
      <button type="button" class="btn" style="width: 100%" @click="$emit('close')">Abbrechen</button>
    </div>
  </Teleport>
</template>

<script setup>
import SheetOptionList from './SheetOptionList.vue'

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
.sheet-header h3 {
  margin: 0;
}
</style>
