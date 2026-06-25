<template>
  <div>
    <h1>Testdruck</h1>
    <p class="muted">Probebons je Station drucken.</p>

    <div class="card">
      <button
        type="button"
        class="btn primary hub-btn"
        :disabled="busy || testPrintBusy"
        @click="doTestPrint"
      >
        Testdruck starten
      </button>
      <p class="muted small">
        Druckt je Station einen Probebons — auch wenn dieselbe Drucker-IP mehrfach vorkommt.
      </p>
    </div>

    <button type="button" class="btn" style="width: 100%; margin-top: 1.5rem" @click="goBack">Zurück</button>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAdminOperations } from '@/composables/useAdminOperations'

const router = useRouter()
const { busy, testPrintBusy, doTestPrint } = useAdminOperations()

function goBack() {
  router.push({ name: 'admin-operations' })
}
</script>

<style scoped>
.small {
  font-size: 0.8rem;
  margin: 0.75rem 0 0;
}
.hub-btn {
  width: 100%;
}
</style>
