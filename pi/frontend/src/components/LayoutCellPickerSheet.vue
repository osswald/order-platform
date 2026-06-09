<template>
  <Teleport to="body">
    <div v-if="open" class="sheet-backdrop" @click.self="$emit('close')" />
    <div v-if="open" class="sheet sheet--picker" role="dialog" aria-modal="true">
      <header class="sheet-header">
        <h3>{{ title || 'Position wählen' }}</h3>
        <p class="muted">Antippen zum Hinzufügen</p>
      </header>
      <SheetScrollBody :active="open">
        <SheetOptionList :items="items" @pick="$emit('pick', $event)" />
      </SheetScrollBody>
      <div class="sheet__footer">
        <button type="button" class="btn" @click="$emit('close')">Abbrechen</button>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import SheetOptionList from './SheetOptionList.vue'
import SheetScrollBody from './SheetScrollBody.vue'

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
.sheet__footer .btn {
  width: 100%;
  min-height: 48px;
  touch-action: manipulation;
}
</style>
