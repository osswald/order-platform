<template>
  <div>
    <h1>Neue Bestellung</h1>
    <TableKeypad hint="Tischnummer eingeben (1–99999)" @submit="onTable" />
    <button type="button" class="btn" style="margin-top: 1rem" @click="router.push({ name: 'hub' })">Zurück</button>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useCart } from '@/composables/useCart'
import TableKeypad from '@/components/TableKeypad.vue'

const router = useRouter()
const { activeTableNumber, clearCart } = useCart()

function onTable(n: number) {
  activeTableNumber.value = n
  clearCart()
  router.push({ name: 'order', query: { table: String(n) } })
}
</script>
