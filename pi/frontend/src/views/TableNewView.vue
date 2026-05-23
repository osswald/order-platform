<template>
  <div>
    <h1>Neue Bestellung</h1>
    <TableKeypad hint="Tischnummer eingeben (1–99999)" @submit="onTable" />
    <button type="button" class="btn" style="margin-top: 1rem" @click="router.push({ name: 'hub' })">Zurück</button>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import * as store from '../store'
import TableKeypad from '../components/TableKeypad.vue'

const router = useRouter()

function onTable(n) {
  store.activeTableNumber.value = n
  store.clearCart()
  router.push({ name: 'order', query: { table: String(n) } })
}
</script>
