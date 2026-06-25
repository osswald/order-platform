<template>
  <div>
    <h1>Pickup Screen</h1>
    <p class="muted">Abholanzeige für fertige Bestellungen öffnen.</p>

    <div v-if="!hasCashRegisters" class="card">
      <p class="muted">Für dieses Event sind keine Kassen konfiguriert.</p>
    </div>

    <div v-else class="card">
      <button type="button" class="btn primary hub-btn" @click="openPickup">
        Pickup Screen öffnen
      </button>
    </div>

    <button type="button" class="btn" style="width: 100%; margin-top: 1.5rem" @click="goBack">Zurück</button>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAdminOperations } from '@/composables/useAdminOperations'

const router = useRouter()
const { hasCashRegisters, openPickup } = useAdminOperations()

function goBack() {
  router.push({ name: 'admin-operations' })
}
</script>

<style scoped>
.hub-btn {
  width: 100%;
}
</style>
