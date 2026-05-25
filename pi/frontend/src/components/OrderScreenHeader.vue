<template>
  <header class="header-bar">
    <button type="button" class="header-btn" aria-label="Zurück" @click="$emit('back')">←</button>
    <div class="header-center">
      <span>{{ table }}</span>
      <span class="sep">|</span>
      <span>{{ totalLabel }}</span>
      <span class="sep">|</span>
      <span>{{ qty }}</span>
    </div>
    <button
      v-if="showMenu"
      type="button"
      class="header-btn menu"
      aria-label="Menü"
      :disabled="disabled"
      @click="$emit('menu')"
    >
      ☰
    </button>
    <button
      type="button"
      class="header-btn fertig"
      :disabled="disabled"
      @click="$emit('submit')"
    >
      FERTIG <span aria-hidden="true">✓</span>
    </button>
  </header>
</template>

<script setup>
defineProps({
  table: { type: [Number, String], required: true },
  totalLabel: { type: String, required: true },
  qty: { type: Number, default: 0 },
  disabled: { type: Boolean, default: false },
  showMenu: { type: Boolean, default: false },
})

defineEmits(['back', 'submit', 'menu'])
</script>
