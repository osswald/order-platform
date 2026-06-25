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

<script setup lang="ts">
withDefaults(
  defineProps<{
    table: number | string
    totalLabel: string
    qty?: number
    disabled?: boolean
    showMenu?: boolean
  }>(),
  { qty: 0, disabled: false, showMenu: false },
)

defineEmits<{
  back: []
  submit: []
  menu: []
}>()
</script>
