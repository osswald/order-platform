<template>
  <div>
    <h1>Tisch abrechnen</h1>
    <TableKeypad hint="Tischnummer für Abrechnung" @submit="onTable" />
    <button type="button" class="btn" style="margin-top: 1rem" @click="router.push({ name: 'hub' })">Zurück</button>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import TableKeypad from '../components/TableKeypad.vue'

const router = useRouter()

function onTable(n) {
  router.push({ name: 'pay-table', query: { table: String(n) } })
}
</script>
